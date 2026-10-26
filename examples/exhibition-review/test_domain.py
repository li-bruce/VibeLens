"""Independent business expectations, exercised without VibeLens installed or running."""

import base64
import unittest
from sqlalchemy import create_engine, select
from domain import Gallery
from repository import Repository, artwork, exhibition, messages


class GalleryRules(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.repository = Repository(self.engine)
        self.gallery = Gallery(self.repository)
        # Signature fixtures exercise the declared header check. The browser case
        # additionally uploads and decodes complete, checksummed PNG files.
        self.image = base64.b64encode(b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR" + b"\0" * 12).decode()

    def tearDown(self):
        self.engine.dispose()

    def upload(self):
        return self.gallery.upload("artist", "Light study", self.image)

    def test_approval_before_upload_does_not_publish_a_missing_image(self):
        self.assertEqual(self.gallery.approve("reviewer", 0)["status"], "no_image")
        self.assertIsNone(self.repository.public()["published_version"])

    def test_replacement_cannot_be_published_by_an_old_preview(self):
        self.upload()
        opened = self.gallery.preview("reviewer")["reviewed_version"]
        self.upload()
        self.assertEqual(self.gallery.approve("reviewer", opened)["status"], "stale_review")
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(artwork.c.status)).scalar_one(), "pending")
            self.assertIsNone(connection.execute(select(exhibition.c.image_version)).scalar())

    def test_fresh_review_publishes_exactly_the_opened_version(self):
        self.upload()
        self.upload()
        opened = self.gallery.preview("reviewer")["reviewed_version"]
        self.assertEqual(self.gallery.approve("reviewer", opened)["published_version"], 2)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(exhibition.c.image_version)).scalar_one(), 2)

    def test_artist_cannot_approve_even_the_current_version(self):
        self.upload()
        self.assertEqual(self.gallery.approve("artist", 1)["status"], "forbidden")
        self.assertIsNone(self.repository.public()["published_version"])

    def test_invalid_content_does_not_create_a_version_or_message(self):
        value = base64.b64encode(b"This is text").decode()
        self.assertEqual(self.gallery.upload("artist", "Text", value)["status"], "invalid_image")
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(artwork.c.image_version)).scalar_one(), 0)
            self.assertIsNone(connection.execute(select(messages.c.id)).first())

    def test_reviewer_cannot_upload_or_replace_an_image(self):
        self.assertEqual(
            self.gallery.upload("reviewer", "Denied", self.image)["status"], "forbidden"
        )
        self.assertEqual(self.repository.read_artwork()["image_version"], 0)

    def test_each_upload_preserves_a_review_message_and_prior_image(self):
        self.upload()
        self.upload()
        self.assertEqual(self.repository.public()["messages"], [1, 2])
        self.assertEqual(self.repository.image(1), self.repository.image(2))


if __name__ == "__main__":
    unittest.main()
