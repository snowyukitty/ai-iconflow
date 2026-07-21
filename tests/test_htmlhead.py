import unittest

from iconflow.htmlhead import WebMetaOptions, asset_path, head_snippet, manifest


class HtmlHeadTests(unittest.TestCase):
    def test_relative_paths_split_head_and_manifest_rules(self):
        opts = WebMetaOptions(relative_paths=True)
        self.assertEqual(asset_path("favicon.ico", opts), "./favicon.ico")
        self.assertEqual(asset_path("icon-192.png", opts, manifest=True), "icon-192.png")

        data = manifest("Demo App", "#111111", "#ffffff", opts)
        self.assertEqual(data["start_url"], ".")
        self.assertEqual(data["scope"], ".")
        self.assertEqual(data["icons"][0]["src"], "icon-192.png")

    def test_manifest_extra_and_head_meta(self):
        opts = WebMetaOptions(
            short_name="Demo",
            description='Demo "icon"',
            categories=["productivity", "tools"],
            manifest_extra={"display_override": ["standalone", "browser"]},
            head_meta={"application-name": "Demo"},
            windows_tiles=True,
            tile_color="#abcdef",
        )
        data = manifest("Demo App", "#111111", "#ffffff", opts)
        self.assertEqual(data["short_name"], "Demo")
        self.assertEqual(data["description"], 'Demo "icon"')
        self.assertEqual(data["categories"], ["productivity", "tools"])
        self.assertEqual(data["display_override"], ["standalone", "browser"])

        head = head_snippet("Demo App", "#111111", "#ffffff", opts)
        self.assertIn('name="description" content="Demo &quot;icon&quot;"', head)
        self.assertIn('name="application-name" content="Demo"', head)
        self.assertIn('name="msapplication-TileColor" content="#abcdef"', head)


if __name__ == "__main__":
    unittest.main()
