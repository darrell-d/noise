from django.core.management.base import BaseCommand, CommandError
from storages.backends.s3boto3 import S3Boto3Storage

from noise.models import Noise


ALL_USERS_URI = "http://acs.amazonaws.com/groups/global/AllUsers"


class Command(BaseCommand):
    help = "Preview or remove anonymous-read ACLs from restricted Noise media."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply private ACLs. Without this flag the command is read-only.",
        )

    @staticmethod
    def _is_anonymously_readable(acl):
        return any(
            grant.get("Permission") in {"READ", "FULL_CONTROL"}
            and grant.get("Grantee", {}).get("URI") == ALL_USERS_URI
            for grant in acl.get("Grants", [])
        )

    def handle(self, *args, **options):
        storage = Noise._meta.get_field("media").storage._backend()
        if not isinstance(storage, S3Boto3Storage):
            raise CommandError("Noise media is not using S3 storage")

        client = storage.connection.meta.client
        bucket = storage.bucket_name
        keys = {
            key
            for key in (
                Noise.objects.exclude(bucket__in=Noise.PUBLIC_BUCKET_ALIASES)
                .exclude(media="")
                .exclude(media__isnull=True)
                .values_list("media", flat=True)
            )
            if key
        }
        checked = public = changed = failed = 0
        for key in sorted(keys):
            checked += 1
            try:
                acl = client.get_object_acl(Bucket=bucket, Key=key)
                if not self._is_anonymously_readable(acl):
                    continue
                public += 1
                if options["apply"]:
                    client.put_object_acl(ACL="private", Bucket=bucket, Key=key)
                    changed += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"Restricted Noise object ACL failed: {type(exc).__name__}")

        mode = "apply" if options["apply"] else "preview"
        self.stdout.write(
            f"mode={mode} checked={checked} anonymous_read={public} "
            f"changed={changed} failed={failed}"
        )
        if failed:
            raise CommandError("One or more restricted Noise ACL operations failed")
