from michat.lib.speak import ChatGPTWithEmotion


def test_chat_with_emotion_text():
    sample_text = '\n\ntest\n感情パラメーター: \n{"喜び": 10}\n\n'
    wanted = "test"
    chat = ChatGPTWithEmotion(512)
    trimed, _ = chat.trim_and_parse(sample_text)
    assert trimed == wanted


def test_chat_with_emotion_params():
    sample_text = '\n\ntest\n感情パラメーター: \n{"喜び": 10}\n\n'
    wanted = {"喜び": 10}
    chat = ChatGPTWithEmotion(512)
    _, params = chat.trim_and_parse(sample_text)
    assert params == wanted
