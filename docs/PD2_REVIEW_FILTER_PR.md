# PR2 enhancement: filter administrator review queue by violation type

This follow-up feature is additive to the complete 1.3 Violation Management module.

- The administrator-only pending-review queue now has an **All types / Overspeeding / Running a red light / Reckless driving** dropdown.
- Type filtering can be combined with existing plate-number or road-location search.
- Invalid type values are ignored; existing role restrictions and permissions are unchanged.
- An HTTP regression test validates filtered, combined, and invalid-filter behavior.

This package contains only four changed/new files to place on a new branch **created from develop after PR1 is merged**.
Do not extract it into main. Do not claim this PR is merged until you actually merge it in GitHub.

Run: `python manage.py check`, then isolated test mode `ROADGUARD_TEST_SQLITE=1` with `python manage.py test accounts violations`.
