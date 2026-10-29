"""
Create (or restore) the demo account and a small, realistic community around it,
so visitors who log in with the demo account land on a populated feed.

Safe to run repeatedly: every seeded object has a fixed id, so re-running updates
the seeded content back to its original state instead of duplicating it. Content
created by real users is never touched.

    python manage.py seed_demo --site-url https://your-app.onrender.com
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from users.demo import COMMENTS, PEOPLE, POSTS, DemoSeedError, seed_all


class Command(BaseCommand):
    help = "Create or restore the demo account and its sample community."

    def add_arguments(self, parser):
        parser.add_argument(
            "--site-url",
            default=os.environ.get("SITE_URL") or os.environ.get("RENDER_EXTERNAL_URL"),
            help="Public URL of the site, e.g. https://tavern.onrender.com "
                 "(defaults to $SITE_URL or Render's $RENDER_EXTERNAL_URL).",
        )

    def handle(self, *args, **options):
        site_url = (options["site_url"] or "").rstrip("/")
        if not site_url.startswith(("http://", "https://")):
            raise CommandError("Pass --site-url (or set SITE_URL) to the site's public URL, e.g. https://tavern.onrender.com")
        try:
            seed_all(site_url)
        except DemoSeedError as error:
            raise CommandError(str(error))

        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready at {site_url}: log in as '{settings.DEMO_USERNAME}' "
            f"({len(PEOPLE)} people, {len(POSTS)} posts, {len(COMMENTS)} comments)."
        ))
