import os

from django.core.management.base import CommandError, BaseCommand

from django.apps import apps
from django.core.files.storage import default_storage
from optparse import make_option

from ._utils import file_patt, file_patt_prefixed


class Command(BaseCommand):
    can_import_settings = True

    def add_arguments(self, parser):
        parser.add_argument('--noinput',
                            action='store_false',
                            dest='interactive',
                            default=True,
                            help="Do NOT prompt the user for input of any kind.")

    def handle(self, **options):
        from django.conf import settings

        app_module_paths = []

        for app in apps.get_app_configs():
            if app.models_module:
                if hasattr(app.models_module, '__path__'):
                    # It's a 'models/' subpackage
                    for path in app.models_module.__path__:
                        app_module_paths.append(path)
                else:
                    # It's a models.py module
                    app_module_paths.append(app.models_module.__file__)

        app_fixtures = [os.path.join(os.path.dirname(path), 'fixtures') for path in app_module_paths]
        app_fixtures += list(settings.FIXTURE_DIRS) + ['']

        json_fixtures = []
        for fixture_path in app_fixtures:
            try:
                root, dirs, files = next(os.walk(fixture_path))
                for file in files:
                    if file.rsplit('.', 1)[-1] == 'json':
                        json_fixtures.append((root, os.path.join(root, file)))
            except StopIteration:
                pass

        if options['interactive']:
            confirm = raw_input("This will overwrite any existing files. Proceed? ")
            if not confirm.lower().startswith('y'):
                raise CommandError("Media syncing aborted")

        if getattr(settings, 'FIXTURE_MEDIA_REQUIRE_PREFIX', False):
            pattern = file_patt_prefixed
        else:
            pattern = file_patt

        for root, fixture in json_fixtures:
            file_paths = pattern.findall(open(fixture).read())
            if file_paths:
                for fp in file_paths:
                    fixture_media = os.path.join(root, 'media')
                    fixture_path = os.path.join(fixture_media, fp)
                    if not os.path.exists(fixture_path):
                        self.stderr.write("File path (%s) found in fixture but not on disk in (%s) \n" % (fp,fixture_path))
                        continue
                    final_dest = os.path.join(settings.MEDIA_ROOT, fp)
                    dest_dir = os.path.dirname(final_dest)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    self.stdout.write('Copied %s to %s\n' % (fp, final_dest))
                    with open(fixture_path, 'rb') as f:
                        default_storage.save(fp, f)
