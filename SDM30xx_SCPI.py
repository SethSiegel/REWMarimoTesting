import socket
import sys
import time


class SDM30xx_SCPI:
    def __init__(self, sdm30xx_ip: str, sdm30xx_port: int):
        """Creates an instance of the SDM30xx_SCPI class given an IP address and port.

        Args:
            sdm30xx_ip (str): IP of the SDM30xx device.
            sdm30xx_port (int): Port of the SDM30xx device. Default is 5025.
        """
        self.sdm30xx_ip = sdm30xx_ip
        self.sdm30xx_port = sdm30xx_port
        self.sdm30xx_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sdm30xx_socket.connect((self.sdm30xx_ip, self.sdm30xx_port))
        except Exception as e:
            print(f"Error connecting to SDM3055 {self.sdm30xx_ip}: {e}")
            return

    def send_command(self, command):
        """Send a command to the SDM3055 device."""
        try:
            self.sdm30xx_socket.sendall((command + '\n').encode('utf-8'))
            time.sleep(0.1)  # Allow some time for the command to be processed
        except socket.error as e:
            print(f"Error sending command '{command}': {e}")

    def read_response(self):
        """Read a response from the SDM3055 device."""
        try:
            response = self.sdm30xx_socket.recv(1024).decode('utf-8').strip()
            return response
        except socket.error as e:
            print(f"Error reading response: {e}")
            return None

    def qeury_command(self, command):
        """Send a read command to the SDM3055 device and return the response."""
        self.send_command(command)
        return self.read_response()

    def close(self):
        """Close the socket connection to the SDM30xx device."""
        self.sdm30xx_socket.close()

    def query_impedance(self, unit_type: str):
        """ Helper function for backend.py to grab Pass Fail for impedance testing

        Args:
            unit_type (str): pass unit type for testing

        Returns:
            boolean: True if the impedance is within range, False otherwise
        """
        unit_types = {
            # temp names
            "ResonX6-Lo": {
                "max": 4.5,
                "min": 3.5
            },
            "ResonX6-Hi": {
                "max": 4.5,
                "min": 3.5
            },
            "ResonX5-Hi": {
                "max": 8.5,
                "min": 7.5
                },
            "ResonX5-Lo": {
                "max": 4.5,
                "min": 3.5
                },
            "Bass Shaker": {
                "max": 16.5,
                "min": 15.5
                },
            "Exciter": {
                "max": 8.5,
                "min": 7.5
                },
            "Thruster": {
                "max": 4.5,
                "min": 3.5
                },
            }
        if unit_type not in unit_types:
            print("Invalid unit type. Please enter one of the following:")
            print(unit_types)
            return False

        # measure the imepdance
        impedance = self.qeury_command("MEAS:FRES? 200")
        try:
            impedance = float(impedance)
        except ValueError:
            print(f"Impedance {impedance} could not be converted to a float")
            return False
        if impedance > unit_types[unit_type]['max']:
            print("PASS: Impedance is out of range")
            return False
        elif impedance < unit_types[unit_type]['min']:
            print("FAIL: Impedance is below the minimum impedance")
            return False
        else:
            return True


def main():
    """Main function to connect to the SDM3055 and send commands."""
    sdm30xx = SDM30xx_SCPI("192.168.1.202", 5025)

    user_command = ""
    while user_command != "quit":
        user_input = input("Enter SEND, READ, QUERY, IMPEDANCE, or QUIT: ")
        user_command = user_input.strip().lower()
        if user_command == "send":
            command = input("Enter command to send: ")
            sdm30xx.send_command(command)
            print(f"Command '{command}' sent.")
        elif user_command == "read":
            response = sdm30xx.read_response()
            if response:
                print(f"Response: {response}")
            else:
                print("No response received.")
        elif user_command == "query":
            command = input("Enter query command: ")
            response = sdm30xx.qeury_command(command)
            if response:
                print(f"Query response: {response}")
                print(float(response))
            else:
                print("No response received.")
        elif user_command == "impedance":
            unit_type = input("Enter the unit type: ")
            if sdm30xx.query_impedance(unit_type):
                print("Impedance is within range")
            else:
                print("Impedance is out of range")
        elif user_command == "quit":
            print("Exiting...")
            sdm30xx.close()
            sys.exit(0)
        else:
            print("Invalid command. Please enter SEND, READ, QUERY, or QUIT.")
            user_command = ""


if __name__ == "__main__":
    # this file can be run as the main script for individual testing purposes
    main()