"""Offline policy and immutable request-boundary checks; no network."""
from unittest import TestCase, main
from unittest.mock import patch
import route_control as r


class RouteTests(TestCase):
    def test_both_authorized_models(self):
        for endpoint, model in (
            ('http://llm-proxy.intra.xiaojukeji.com', 'deepseek-v4-pro'),
            ('https://api.deepseek.com/v1/', 'deepseek-flash'),
        ):
            with patch.object(r.c, 'load_dotenv'), patch.dict(r.os.environ, {'OPENAI_BASE_URL': endpoint}):
                self.assertEqual(r.current_route()['evolution'], model)

    def test_route_must_match_freeze(self):
        old = r.routing.model_route('https://api.deepseek.com', 'deepseek-v4-flash', 'deepseek-v4-pro')
        new = r.routing.model_route('http://llm-proxy.intra.xiaojukeji.com', 'deepseek-v4-flash', 'deepseek-v4-pro')
        protocol = {'endpoint_route': old, 'cases': [{'parameters': {'model': old['evolution']}}] * 8}
        with patch.object(r.c, 'verify'), patch.object(r.c, 'read', return_value=protocol):
            with patch.object(r, 'current_route', return_value=old):
                self.assertEqual(r.checked_route()[0], old)
            with patch.object(r, 'current_route', return_value=new):
                with self.assertRaisesRegex(AssertionError, 'changed after freeze'):
                    r.checked_route()


if __name__ == '__main__':
    main()
