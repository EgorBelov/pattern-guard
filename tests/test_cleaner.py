from app.preprocessor.cleaner import TextCleaner

def test_links():
    c, m = TextCleaner().clean("перейди https://t.me/x")
    assert m.has_links is True

def test_caps():
    c, m = TextCleaner().clean("ЭТО КАПС")
    assert m.caps_ratio > 0.5

def test_homoglyphs():
    c, m = TextCleaner().clean("привет aдмин")
    assert "а" in c

def test_compress():
    c, m = TextCleaner().clean("шуууутккааа")
    assert c == "шутка"

def test_contacts():
    c, m = TextCleaner().clean("пиши @user или +7 999 123-45-67")
    assert m.has_contacts is True
