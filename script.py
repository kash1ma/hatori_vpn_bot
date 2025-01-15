import os
import subprocess
from pathlib import Path

# Configuration
EASYRSA_DIR = "/etc/openvpn/easy-rsa"
OUTPUT_DIR = "/root/clients"
TEMPLATE_OVPN = "/root/client-template.ovpn"
TA_KEY_PATH = "/etc/openvpn/certs/ta.key"

# Ensure output directory exists
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def generate_client(client_name):
    """Generate a client certificate and .ovpn file."""
    try:
        # Navigate to EasyRSA directory
        os.chdir(EASYRSA_DIR)

        # Generate the client certificate
        subprocess.run(["./easyrsa", "build-client-full", client_name, "nopass"], check=True)

        # Define file paths
        key_file = Path(EASYRSA_DIR) / "pki" / "private" / f"{client_name}.key"
        crt_file = Path(EASYRSA_DIR) / "pki" / "issued" / f"{client_name}.crt"
        ca_file = Path(EASYRSA_DIR) / "pki" / "ca.crt"
        ta_file = Path(TA_KEY_PATH)

        # Ensure all required files exist
        for file in [key_file, crt_file, ca_file, ta_file]:
            if not file.exists():
                raise FileNotFoundError(f"Required file not found: {file}")

        # Read the template .ovpn file
        with open(TEMPLATE_OVPN, "r") as template:
            config = template.read()

        # Append certificates and keys to the .ovpn configuration
        config += "\n<ca>\n" + ca_file.read_text() + "\n</ca>"
        config += "\n<cert>\n" + crt_file.read_text() + "\n</cert>"
        config += "\n<key>\n" + key_file.read_text() + "\n</key>"
        config += "\n<tls-auth>\n" + ta_file.read_text() + "\n</tls-auth>"

        # Save the .ovpn file
        output_file = Path(OUTPUT_DIR) / f"{client_name}.ovpn"
        with open(output_file, "w") as f:
            f.write(config)

        print(f"Client configuration generated: {output_file}")

    except subprocess.CalledProcessError as e:
        print(f"Error during OpenVPN client generation: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    client_name = input("Enter the client name: ").strip()
    if client_name:
        generate_client(client_name)
    else:
        print("Client name cannot be empty.")