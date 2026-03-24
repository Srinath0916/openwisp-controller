import swapper

from .base.models import (
    AbstractCommand,
    AbstractCredentials,
    AbstractDeviceConnection,
    AbstractMassCommand,
)


class Credentials(AbstractCredentials):
    class Meta(AbstractCredentials.Meta):
        abstract = False
        swappable = swapper.swappable_setting("connection", "Credentials")


class DeviceConnection(AbstractDeviceConnection):
    class Meta(AbstractDeviceConnection.Meta):
        abstract = False
        swappable = swapper.swappable_setting("connection", "DeviceConnection")


class MassCommand(AbstractMassCommand):
    class Meta(AbstractMassCommand.Meta):
        abstract = False
        swappable = swapper.swappable_setting("connection", "MassCommand")


class Command(AbstractCommand):
    class Meta(AbstractCommand.Meta):
        abstract = False
        swappable = swapper.swappable_setting("connection", "Command")

