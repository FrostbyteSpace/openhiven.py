import openhivenpy
import asyncio

token_ = ""


def test_start(token):
    global token_
    token_ = token


class TestUserClient:
    def test_init(self):
        client = openhivenpy.UserClient(token_)
        assert client.token == token_
        assert client.client_type == 'user'
        assert client.connection.heartbeat == 30000
        assert client.connection.close_timeout == 60

        @client.event()
        async def on_ready():
            print("\non_ready was called!")
            await client.close()

        client.run()
