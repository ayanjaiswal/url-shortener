from app.codes import ALPHABET, CODE_LENGTH, generate_code, is_valid_code


def test_generated_code_has_right_length_and_characters():
    for _ in range(200):
        code = generate_code()
        assert len(code) == CODE_LENGTH
        assert all(char in ALPHABET for char in code)


def test_generated_codes_do_not_repeat():
    codes = {generate_code() for _ in range(1000)}
    assert len(codes) == 1000


def test_is_valid_code():
    assert is_valid_code("aB3xK9q")
    assert not is_valid_code("short")  # too short
    assert not is_valid_code("waytoolong1")  # too long
    assert not is_valid_code("aB3xK9!")  # bad character
    assert not is_valid_code("")
