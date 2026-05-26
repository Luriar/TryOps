import pytest
from stage0.rfid_synthesizer import RFIDSynthesizer

def test_synthesizer_mock():
    # Will use mock data since paths are fake
    synth = RFIDSynthesizer("fake_articles.csv", "fake_transactions.csv")
    articles, transactions = synth.load_and_filter_data()
    
    assert len(articles) > 0
    
    events = synth.synthesize_events(1000, num_sessions=5, hesitation_ratio=1.0)
    # 5 sessions. Each has hesitation, meaning 2 enters and 1 exit.
    # Total events = 5 * 3 = 15
    assert len(events) == 15
    
    enters = [e for e in events if e["event_type"] == "enter"]
    assert len(enters) == 10
