import unittest

from api_builder import new_builder


class ApiBuilderTests(unittest.TestCase):
    def test_build_get_url_with_path_and_query(self):
        builder = (
            new_builder("https://jsonplaceholder.typicode.com")
            .path("posts", "1")
            .query(include="comments", page=1)
            .header("Accept", "application/json")
            .get()
        )

        self.assertEqual(
            builder.build_url(),
            "https://jsonplaceholder.typicode.com/posts/1?include=comments&page=1",
        )

        request = builder.build()
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.headers["Accept"], "application/json")

    def test_build_post_request(self):
        builder = (
            new_builder("https://api.example.com")
            .path("users")
            .post({"name": "Bora", "role": "admin"})
        )

        request = builder.build()

        self.assertEqual(request.get_method(), "POST")
        self.assertIn("Content-type", request.headers)
        self.assertEqual(request.data, b'{"name": "Bora", "role": "admin"}')


if __name__ == "__main__":
    unittest.main()
