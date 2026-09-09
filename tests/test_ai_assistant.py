import json
import unittest
from unittest.mock import patch

from Zuvio import ZuvioBot, build_ai_messages, request_ai_suggestion


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class FakeElement:
    def __init__(self, text='', element_id='', unanswered=False, has_image=False):
        self.text = text
        self.element_id = element_id
        self.unanswered = unanswered
        self.has_image = has_image
        self.screenshot_as_base64 = 'question-image'

    def find_elements(self, by, value):
        if value == 'i-c-l-q-q-b-b-mini-box-gray':
            return [object()] if self.unanswered else []
        if value == 'i-c-l-q-q-b-title':
            return [FakeElement(self.text)]
        if value == "img, canvas, [style*='background-image']":
            return [object()] if self.has_image else []
        return []

    def get_attribute(self, name):
        return self.element_id if name == 'data-question-id' else ''

    def is_displayed(self):
        return True


class FakeDriver:
    def __init__(self, cards, detail):
        self.cards = cards
        self.detail = detail
        self.clicked = []

    def get(self, url):
        self.url = url

    def find_elements(self, by, value):
        if value == 'i-c-l-q-question-box':
            return self.cards
        if value == ".i-answer-content, [class*='i-a-c-q-t-q-b']":
            return [self.detail]
        return []

    def execute_script(self, script, element):
        self.clicked.append(element)


class FakeWait:
    def __init__(self, driver, timeout):
        self.driver = driver

    def until(self, condition):
        return condition(self.driver)


class AiAssistantTests(unittest.TestCase):
    def test_build_messages_attaches_question_image(self):
        messages = build_ai_messages('Question and choices', 'image-data')

        user_content = messages[1]['content']
        self.assertEqual(user_content[0]['type'], 'text')
        self.assertIn('Question and choices', user_content[0]['text'])
        self.assertEqual(
            user_content[1]['image_url']['url'],
            'data:image/png;base64,image-data'
        )

    @patch('Zuvio.urllib.request.urlopen')
    def test_request_uses_bearer_token_and_returns_text(self, urlopen):
        urlopen.return_value = FakeResponse({
            'choices': [{'message': {'content': ' Suggested answer '}}]
        })

        result = request_ai_suggestion(
            'https://example.com/v1/chat/completions',
            'secret-token',
            'test-model',
            'Question'
        )

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        self.assertEqual(request.get_header('Authorization'), 'Bearer secret-token')
        self.assertEqual(payload['model'], 'test-model')
        self.assertEqual(result, 'Suggested answer')

    @patch('Zuvio.urllib.request.urlopen')
    def test_request_supports_list_response_content(self, urlopen):
        urlopen.return_value = FakeResponse({
            'choices': [{'message': {'content': [
                {'type': 'text', 'text': 'First'},
                {'type': 'text', 'text': 'Second'}
            ]}}]
        })

        result = request_ai_suggestion(
            'https://example.com/v1/chat/completions',
            'secret-token',
            'test-model',
            'Question'
        )

        self.assertEqual(result, 'First\nSecond')

    @patch('Zuvio.urllib.request.urlopen')
    def test_request_rejects_empty_response_content(self, urlopen):
        urlopen.return_value = FakeResponse({
            'choices': [{'message': {'content': '  '}}]
        })

        with self.assertRaisesRegex(ValueError, '未回傳作答建議'):
            request_ai_suggestion(
                'https://example.com/v1/chat/completions',
                'secret-token',
                'test-model',
                'Question'
            )

    @patch('Zuvio.WebDriverWait', FakeWait)
    def test_extractor_skips_seen_question_and_captures_visual_question(self):
        seen = FakeElement('Seen question', 'seen-id', unanswered=True)
        active = FakeElement('Active question', 'active-id', unanswered=True)
        detail = FakeElement(
            'Active question\nA. First\nB. Second',
            has_image=True
        )
        driver = FakeDriver([seen, active], detail)
        bot = ZuvioBot()
        bot.driver = driver
        bot.ai_seen_questions.add('seen-id')

        question = bot.get_unanswered_question('course-1')

        self.assertEqual(
            question,
            ('active-id', 'Active question\nA. First\nB. Second', 'question-image')
        )
        self.assertEqual(driver.clicked, [active])


if __name__ == '__main__':
    unittest.main()
