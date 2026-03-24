# Generated prototype migration for Mass Commands feature

import collections
import uuid

import django.db.models.deletion
import jsonfield.fields
from django.conf import settings
from django.db import migrations, models

import openwisp_controller.connection.commands


class Migration(migrations.Migration):

    dependencies = [
        ('geo', '0003_alter_devicelocation_floorplan_location'),
        ('config', '0061_config_checksum_db'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('connection', '0009_alter_deviceconnection_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='MassCommand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('target_type', models.CharField(choices=[('organization', 'Organization'), ('group', 'Device Group'), ('location', 'Geographic Location'), ('manual', 'Selected Devices')], db_index=True, max_length=20)),
                ('type', models.CharField(choices=openwisp_controller.connection.commands.get_command_choices, max_length=16)),
                ('input', jsonfield.fields.JSONField(blank=True, dump_kwargs={'indent': 4}, load_kwargs={'object_pairs_hook': collections.OrderedDict}, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in-progress', 'In Progress'), ('completed', 'Completed')], db_index=True, default='pending', max_length=20)),
                ('total_devices', models.IntegerField(default=0)),
                ('successful', models.IntegerField(default=0)),
                ('failed', models.IntegerField(default=0)),
                ('in_progress', models.IntegerField(default=0)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mass_commands', to=settings.AUTH_USER_MODEL)),
                ('devices', models.ManyToManyField(blank=True, to='config.Device')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='config.DeviceGroup')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='geo.Location')),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='openwisp_users.Organization')),
            ],
            options={
                'verbose_name': 'Mass Command',
                'verbose_name_plural': 'Mass Commands',
                'ordering': ('-created',),
                'abstract': False,
                'swappable': 'CONNECTION_MASSCOMMAND_MODEL',
            },
        ),
        migrations.AddField(
            model_name='command',
            name='mass_command',
            field=models.ForeignKey(blank=True, help_text='Mass command this command belongs to', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='commands', to='connection.MassCommand'),
        ),
    ]
