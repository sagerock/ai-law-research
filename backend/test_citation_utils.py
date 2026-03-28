import pytest
from citation_utils import (
    reporter_cite_to_slug,
    slug_to_reporter_cite,
    parse_citation_slug,
    case_title_to_slug,
    build_canonical_slug,
)


class TestReporterCiteToSlug:
    def test_us_reports(self):
        assert reporter_cite_to_slug("550 U.S. 544") == "550-us-544"

    def test_federal_reporter_2d(self):
        assert reporter_cite_to_slug("457 F.2d 365") == "457-f2d-365"

    def test_federal_reporter_3d(self):
        assert reporter_cite_to_slug("103 F.3d 144") == "103-f3d-144"

    def test_federal_reporter_4th(self):
        assert reporter_cite_to_slug("12 F.4th 100") == "12-f4th-100"

    def test_federal_appendix(self):
        assert reporter_cite_to_slug("206 F. App'x 317") == "206-f-appx-317"

    def test_federal_supplement(self):
        assert reporter_cite_to_slug("100 F. Supp. 200") == "100-f-supp-200"

    def test_federal_supplement_2d(self):
        assert reporter_cite_to_slug("100 F. Supp. 2d 200") == "100-f-supp-2d-200"

    def test_cal_2d(self):
        assert reporter_cite_to_slug("51 Cal. 2d 409") == "51-cal-2d-409"

    def test_ne(self):
        assert reporter_cite_to_slug("118 N.E. 1082") == "118-ne-1082"

    def test_ne2d(self):
        assert reporter_cite_to_slug("100 N.E.2d 50") == "100-ne2d-50"

    def test_ny(self):
        assert reporter_cite_to_slug("124 N.Y. 538") == "124-ny-538"

    def test_ny2d(self):
        assert reporter_cite_to_slug("50 N.Y.2d 100") == "50-ny2d-100"

    def test_us_app_dc(self):
        assert reporter_cite_to_slug("121 U.S. App. D.C. 315") == "121-us-app-dc-315"

    def test_s_ct(self):
        assert reporter_cite_to_slug("100 S. Ct. 200") == "100-s-ct-200"

    def test_l_ed(self):
        assert reporter_cite_to_slug("100 L. Ed. 200") == "100-l-ed-200"

    def test_l_ed_2d(self):
        assert reporter_cite_to_slug("100 L. Ed. 2d 200") == "100-l-ed-2d-200"

    def test_bankruptcy_reporter(self):
        assert reporter_cite_to_slug("100 B.R. 200") == "100-b-r-200"

    def test_p2d(self):
        assert reporter_cite_to_slug("474 P.2d 689") == "474-p2d-689"

    def test_so_2d(self):
        assert reporter_cite_to_slug("100 So. 2d 200") == "100-so-2d-200"

    def test_sw2d(self):
        assert reporter_cite_to_slug("100 S.W.2d 200") == "100-sw2d-200"

    def test_ohio_op(self):
        assert reporter_cite_to_slug("11 Ohio Op. 246") == "11-ohio-op-246"

    def test_a2d(self):
        assert reporter_cite_to_slug("100 A.2d 200") == "100-a2d-200"

    def test_va(self):
        assert reporter_cite_to_slug("196 Va. 493") == "196-va-493"

    def test_mass(self):
        assert reporter_cite_to_slug("100 Mass. 200") == "100-mass-200"

    def test_trailing_year(self):
        assert reporter_cite_to_slug("477 U.S. 317 (1986)") == "477-us-317"

    def test_trailing_court_and_year(self):
        assert reporter_cite_to_slug("479 P.2d 946 (Wash. Ct. App. 1971)") == "479-p2d-946"

    def test_multiple_cites_comma_separated(self):
        assert reporter_cite_to_slug("248 N.Y. 339, 162 N.E. 99 (1928)") == "248-ny-339"


class TestSlugToReporterCite:
    def test_us(self):
        assert slug_to_reporter_cite("550-us-544") == "550 U.S. 544"

    def test_f3d(self):
        assert slug_to_reporter_cite("103-f3d-144") == "103 F.3d 144"

    def test_f_appx(self):
        assert slug_to_reporter_cite("206-f-appx-317") == "206 F. App'x 317"

    def test_cal_2d(self):
        assert slug_to_reporter_cite("51-cal-2d-409") == "51 Cal. 2d 409"

    def test_us_app_dc(self):
        assert slug_to_reporter_cite("121-us-app-dc-315") == "121 U.S. App. D.C. 315"

    def test_l_ed_2d(self):
        assert slug_to_reporter_cite("100-l-ed-2d-200") == "100 L. Ed. 2d 200"

    def test_ohio_st3d(self):
        assert slug_to_reporter_cite("6-ohio-st3d-155") == "6 Ohio St.3d 155"


class TestParseCitationSlug:
    def test_simple_citation(self):
        assert parse_citation_slug("550-us-544") == ("550", "U.S.", "544")

    def test_multi_part_reporter(self):
        assert parse_citation_slug("121-us-app-dc-315") == ("121", "U.S. App. D.C.", "315")

    def test_not_a_citation(self):
        assert parse_citation_slug("wood-v-lucy-lady-duff-gordon") is None

    def test_pure_number(self):
        assert parse_citation_slug("145730") is None


class TestCaseTitleToSlug:
    def test_basic(self):
        assert case_title_to_slug("Bell Atlantic Corp. v. Twombly") == "bell-atlantic-corp-v-twombly"

    def test_with_comma(self):
        assert case_title_to_slug("Wood v. . Lucy, Lady Duff-Gordon") == "wood-v-lucy-lady-duff-gordon"

    def test_strips_leading_trailing_hyphens(self):
        slug = case_title_to_slug("  Erie Railroad Co. v. Tompkins  ")
        assert not slug.startswith("-")
        assert not slug.endswith("-")

    def test_collapses_multiple_hyphens(self):
        slug = case_title_to_slug("Hamer v. . Sidway")
        assert "--" not in slug


class TestBuildCanonicalSlug:
    def test_with_reporter_cite(self):
        assert build_canonical_slug("550 U.S. 544", "Bell Atlantic Corp. v. Twombly") == "550-us-544"

    def test_without_reporter_cite(self):
        assert build_canonical_slug(None, "Wood v. Lucy, Lady Duff-Gordon") == "wood-v-lucy-lady-duff-gordon"

    def test_empty_reporter_cite(self):
        assert build_canonical_slug("", "Wood v. Lucy, Lady Duff-Gordon") == "wood-v-lucy-lady-duff-gordon"


class TestRoundtrip:
    def test_roundtrip_cite_to_slug_to_cite(self):
        original = "550 U.S. 544"
        slug = reporter_cite_to_slug(original)
        restored = slug_to_reporter_cite(slug)
        assert restored == original

    def test_roundtrip_f3d(self):
        original = "103 F.3d 144"
        slug = reporter_cite_to_slug(original)
        restored = slug_to_reporter_cite(slug)
        assert restored == original
