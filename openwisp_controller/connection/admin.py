from datetime import timedelta

import reversion
import swapper
from django import forms
from django.contrib import admin
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import path, resolve
from django.utils.html import format_html
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from openwisp_users.multitenancy import MultitenantOrgFilter
from openwisp_utils.admin import TimeReadonlyAdminMixin

from ..admin import MultitenantAdminMixin
from ..config.admin import DeactivatedDeviceReadOnlyMixin, DeviceAdmin
from .schema import schema
from .widgets import CommandSchemaWidget, CredentialsSchemaWidget

Credentials = swapper.load_model("connection", "Credentials")
DeviceConnection = swapper.load_model("connection", "DeviceConnection")
Command = swapper.load_model("connection", "Command")


class CredentialsForm(forms.ModelForm):
    class Meta:
        exclude = []
        widgets = {"params": CredentialsSchemaWidget}


class CommandForm(forms.ModelForm):
    class Meta:
        exclude = []
        widgets = {"input": CommandSchemaWidget}


@admin.register(Credentials)
class CredentialsAdmin(MultitenantAdminMixin, TimeReadonlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "connector",
        "auto_add",
        "created",
        "modified",
    )
    list_filter = [MultitenantOrgFilter, "connector"]
    list_select_related = ("organization",)
    form = CredentialsForm
    fields = [
        "connector",
        "name",
        "organization",
        "auto_add",
        "params",
        "created",
        "modified",
    ]

    def get_urls(self):
        options = getattr(self.model, "_meta")
        url_prefix = f"{options.app_label}_{options.model_name}"
        return [
            path(
                "ui/schema.json",
                self.admin_site.admin_view(self.schema_view),
                name=f"{url_prefix}_schema",
            )
        ] + super().get_urls()

    def schema_view(self, request):
        return JsonResponse(schema)


class DeviceConnectionInline(
    MultitenantAdminMixin, DeactivatedDeviceReadOnlyMixin, admin.StackedInline
):
    model = DeviceConnection
    verbose_name = _("Credentials")
    verbose_name_plural = verbose_name
    exclude = ["params", "created", "modified"]
    readonly_fields = ["is_working", "failure_reason", "last_attempt"]
    extra = 0

    multitenant_shared_relations = ("credentials",)

    def get_queryset(self, request):
        """
        Override MultitenantAdminMixin.get_queryset() because it breaks
        """
        return super(admin.StackedInline, self).get_queryset(request)


class LimitedCommandResults(forms.models.BaseInlineFormSet):
    """Limits results to 30"""

    def get_queryset(self):
        return super().get_queryset()[0:30]


class CommandInline(admin.StackedInline):
    model = Command
    verbose_name = _("Recent Commands")
    verbose_name_plural = verbose_name
    fields = [
        "status_display",
        "type",
        "input_data",
        "output_data",
        "created",
        "modified",
    ]
    readonly_fields = [
        "status_display",
        "type",
        "input_data",
        "output_data",
        "created",
        "modified",
    ]
    formset = LimitedCommandResults

    def get_queryset(self, request, select_related=True):
        """
        Return the most recent commands for this device
        (created within the last 7 days)
        """
        qs = super().get_queryset(request)
        resolved = resolve(request.path_info)
        if "object_id" in resolved.kwargs:
            seven_days = localtime() - timedelta(days=7)
            qs = qs.filter(
                device_id=resolved.kwargs["object_id"], created__gte=seven_days
            ).order_by("-created")
        if select_related:
            qs = qs.select_related()
        return qs

    def input_data(self, obj):
        return obj.input_data

    def output_data(self, obj):
        if obj.status == "in-progress":
            return format_html(
                '<div class="loader recent-commands-loader"></div>',
            )
        return obj.output

    def status_display(self, obj):
        status_value = obj.status
        css_class = f"command-status {status_value}"
        return format_html(
            '<span class="{0}">{1}</span>',
            css_class,
            obj.get_status_display(),
        )

    input_data.short_description = _("input")
    output_data.short_description = _("output")
    status_display.short_description = _("status")

    def _get_conditional_queryset(self, request, obj, select_related=False):
        return self.get_queryset(request, select_related=select_related).exists()

    def has_delete_permission(self, request, obj):
        return False

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj):
        return False


class CommandWritableInline(DeactivatedDeviceReadOnlyMixin, admin.StackedInline):
    model = Command
    extra = 1
    form = CommandForm
    fields = ["type", "input"]

    def get_queryset(self, request, select_related=True):
        return self.model.objects.none()

    def _get_conditional_queryset(self, request, obj, select_related=False):
        return bool(obj) and self.has_change_permission(request, obj)

    def get_urls(self):
        options = self.model._meta
        url_prefix = f"{options.app_label}_{options.model_name}"
        return [
            path(
                f"{options.app_label}/{options.model_name}/ui/schema.json",
                self.admin_site.admin_view(self.schema_view),
                name=f"{url_prefix}_schema",
            ),
        ]

    def schema_view(self, request):
        organization_id = request.GET.get("organization_id")
        if not request.user.is_superuser and (
            not organization_id or not request.user.is_manager(organization_id)
        ):
            return HttpResponseForbidden()
        result = self.model.get_org_schema(organization_id=organization_id)
        return JsonResponse(result)


DeviceAdmin.inlines += [DeviceConnectionInline]
reversion.register(model=DeviceConnection, follow=["device"])
DeviceAdmin.conditional_inlines += [
    CommandWritableInline,
    # this inline must come after CommandWritableInline
    # or the JS logic will not work
    CommandInline,
]
DeviceAdmin.add_reversion_following(follow=["deviceconnection_set"])


# Mass Command Admin
MassCommand = swapper.load_model("connection", "MassCommand")


class MassCommandForm(forms.ModelForm):
    class Meta:
        model = MassCommand
        fields = ['type', 'input']
        widgets = {'input': CommandSchemaWidget}


@admin.register(MassCommand)
class MassCommandAdmin(MultitenantAdminMixin, TimeReadonlyAdminMixin, admin.ModelAdmin):
    list_display = [
        'id',
        'target_type',
        'type',
        'status',
        'total_devices',
        'successful',
        'failed',
        'created',
        'created_by',
    ]
    list_filter = [
        'status',
        'target_type',
        'type',
        MultitenantOrgFilter,
        'created',
    ]
    readonly_fields = [
        'target_type',
        'organization',
        'group',
        'location',
        'status',
        'total_devices',
        'successful',
        'failed',
        'in_progress',
        'created_by',
        'created',
        'modified',
    ]
    fields = [
        'target_type',
        'organization',
        'group',
        'location',
        'type',
        'input',
        'status',
        'total_devices',
        'successful',
        'failed',
        'in_progress',
        'created_by',
        'created',
        'modified',
    ]
    list_select_related = ('organization', 'group', 'location', 'created_by')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Admin action for executing mass commands on selected devices
class ExecuteMassCommandForm(forms.Form):
    type = forms.ChoiceField(
        label=_('Command Type'),
        choices=[],
        required=True,
    )
    input = forms.JSONField(
        label=_('Command Input'),
        required=False,
        widget=CommandSchemaWidget,
        help_text=_('JSON input for the command'),
    )

    def __init__(self, *args, **kwargs):
        org_id = kwargs.pop('org_id', None)
        super().__init__(*args, **kwargs)
        if org_id:
            self.fields['type'].choices = Command.get_org_allowed_commands(org_id)


@admin.action(
    description=_("Execute command on selected devices"),
    permissions=['change']
)
def execute_mass_command_action(modeladmin, request, queryset):
    from django.contrib import messages
    from django.contrib.admin import helpers
    from django.http import HttpResponseRedirect
    from django.template.response import TemplateResponse
    from django.urls import reverse

    org_id = None
    if queryset:
        org_id = queryset[0].organization_id

    if not request.user.is_superuser and not request.user.is_manager(org_id):
        return HttpResponseForbidden()

    if len(queryset) != queryset.filter(organization_id=org_id).count():
        modeladmin.message_user(
            request,
            _("Select devices from one organization"),
            messages.ERROR,
        )
        return HttpResponseRedirect(request.get_full_path())

    if 'apply' in request.POST:
        form = ExecuteMassCommandForm(data=request.POST, org_id=org_id)
        if form.is_valid():
            mass_cmd = MassCommand.objects.create(
                target_type='manual',
                type=form.cleaned_data['type'],
                input=form.cleaned_data.get('input'),
                created_by=request.user,
                status='pending',
            )
            mass_cmd.devices.set(queryset)
            mass_cmd.total_devices = queryset.count()
            mass_cmd.save()

            modeladmin.message_user(
                request,
                _(f"Mass command created successfully for {queryset.count()} devices."),
                messages.SUCCESS,
            )
            return HttpResponseRedirect(
                reverse('admin:connection_masscommand_change', args=[mass_cmd.id])
            )

    form = ExecuteMassCommandForm(org_id=org_id)
    context = {
        'title': _('Execute Command on Selected Devices'),
        'queryset': queryset,
        'form': form,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'opts': modeladmin.model._meta,
        'changelist_url': (
            f"{request.resolver_match.app_name}:"
            f"{request.resolver_match.url_name}"
        ),
    }

    return TemplateResponse(
        request,
        'admin/connection/execute_mass_command.html',
        context,
    )


# Add the action to DeviceAdmin
if hasattr(DeviceAdmin, 'actions'):
    if isinstance(DeviceAdmin.actions, list):
        DeviceAdmin.actions.append(execute_mass_command_action)
    else:
        DeviceAdmin.actions = list(DeviceAdmin.actions) + [execute_mass_command_action]
