import os
import unittest
from io import StringIO
from unittest.mock import patch

from notion_management.cli import main
from notion_management.config import Settings


class ConfigTest(unittest.TestCase):
    def test_missing_environment_leaves_source_ids_empty(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch("notion_management.config._load_dotenv"):
            settings = Settings.from_environment()
        self.assertEqual("", settings.tasks_id)
        self.assertEqual("", settings.manager_id)
        self.assertEqual((), settings.team_member_ids)

    def test_doctor_reports_missing_source_ids_instead_of_masking_with_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch("notion_management.config._load_dotenv"), \
                patch("sys.argv", ["hive-notion", "doctor"]), patch("sys.stdout", new_callable=StringIO) as out:
            exit_code = main()
        self.assertEqual(2, exit_code)
        self.assertIn("NOTION_TASKS_DATA_SOURCE_ID", out.getvalue())
        self.assertIn("NOTION_MANAGER_ID", out.getvalue())


if __name__ == "__main__":
    unittest.main()
