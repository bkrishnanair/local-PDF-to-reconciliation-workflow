from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_review_flow_and_session_status():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert app.subheader[0].value == "HOLD_FOR_REVIEW"
    assert [m.value for m in app.metric] == ["$1,200.00", "$1,350.00", "$150.00"]
    app.sidebar.selectbox[0].select("invoice_b_scanned.pdf").run()
    assert not app.exception
    assert app.subheader[0].value == "MATCHED_DRAFT"
    review = next(s for s in app.selectbox if s.label == "Human review status")
    review.select("Reviewed").run()
    app.sidebar.selectbox[0].select("invoice_a_digital.pdf").run()
    app.sidebar.selectbox[0].select("invoice_b_scanned.pdf").run()
    assert next(s for s in app.selectbox if s.label == "Human review status").value == "Reviewed"
    app.sidebar.text_input[0].set_value("-1").run()
    assert not app.exception
    assert "nonnegative" in app.error[0].value
