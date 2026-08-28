import unittest

from port_detector import PortDetector, PortOwner, parse_proc_net


class FakeDocker:
    def list_port_owners(self):
        return {
            38082: [
                PortOwner(
                    source="docker",
                    protocol="tcp",
                    name="docker-port-hub",
                    image="example/image:latest",
                    private_port=80,
                    bind_ip="0.0.0.0",
                )
            ]
        }


class FakeDetector(PortDetector):
    def __init__(self):
        self.docker = FakeDocker()
        self.proc_root = "/path/that/does/not/exist"


class PortDetectorTests(unittest.TestCase):
    def test_parse_tcp_listen_only(self):
        lines = [
            "sl local_address rem_address st tx_queue",
            "0: 00000000:94C2 00000000:0000 0A 00000000:00000000",
            "1: 0100007F:94C3 0100007F:0050 01 00000000:00000000",
        ]
        result = parse_proc_net(lines, "tcp")
        self.assertIn(38082, result)
        self.assertNotIn(38083, result)

    def test_check_docker_port(self):
        result = FakeDetector().check(38082)
        self.assertFalse(result["available"])
        self.assertEqual("docker-port-hub", result["owners"][0]["name"])

    def test_find_free_port(self):
        self.assertEqual(
            [38080, 38081, 38083],
            FakeDetector().find_free(38080, 38083, 3),
        )

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            FakeDetector().find_free(40000, 39999)


if __name__ == "__main__":
    unittest.main()
