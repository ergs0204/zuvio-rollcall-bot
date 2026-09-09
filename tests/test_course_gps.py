import unittest

from Zuvio import ZuvioBot


class FakeDriver:
    def __init__(self):
        self.commands = []

    def execute_cdp_cmd(self, command, params):
        self.commands.append((command, params))


class CourseGpsTests(unittest.TestCase):
    def setUp(self):
        self.bot = ZuvioBot()
        self.driver = FakeDriver()
        self.bot.driver = self.driver

    def test_course_location_overrides_global_location(self):
        self.bot.default_location = (25.0, 121.0)
        self.bot.current_location = self.bot.default_location
        self.bot.course_gps = {'course-1': '24.5, 120.5'}

        self.bot.apply_course_location('course-1', 'Course 1')

        self.assertEqual(
            self.driver.commands,
            [('Emulation.setGeolocationOverride', {
                'latitude': 24.5,
                'longitude': 120.5,
                'accuracy': 100
            })]
        )

    def test_course_without_override_restores_global_location(self):
        self.bot.default_location = (25.0, 121.0)
        self.bot.current_location = (24.5, 120.5)

        self.bot.apply_course_location('course-2', 'Course 2')

        self.assertEqual(
            self.driver.commands[0],
            ('Emulation.setGeolocationOverride', {
                'latitude': 25.0,
                'longitude': 121.0,
                'accuracy': 100
            })
        )

    def test_course_without_override_clears_location_when_no_global_exists(self):
        self.bot.default_location = None
        self.bot.current_location = (24.5, 120.5)

        self.bot.apply_course_location('course-2', 'Course 2')

        self.assertEqual(
            self.driver.commands[0],
            ('Emulation.clearGeolocationOverride', {})
        )

    def test_repeated_location_does_not_send_duplicate_cdp_command(self):
        self.bot.default_location = None
        self.bot.current_location = (24.5, 120.5)
        self.bot.course_gps = {'course-1': '24.5, 120.5'}

        self.bot.apply_course_location('course-1', 'Course 1')

        self.assertEqual(self.driver.commands, [])


if __name__ == '__main__':
    unittest.main()
