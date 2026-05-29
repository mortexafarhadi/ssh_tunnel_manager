# SSH Tunnel Manager

A robust, cross-platform GUI application built with **PyQt5** to simplify SSH tunnel management. It allows users to effortlessly manage multiple server profiles, maintain stable connections via `autossh`, and automatically toggle system-wide SOCKS proxy settings.

## Key Features

* **Multi-Server Management:** Store and organize multiple SSH server configurations.
* **Persistent Connections:** Integrated with `autossh` to ensure tunnels remain active and reconnect automatically if the connection drops.
* **System-Wide Proxy Automation:**
    * **On Connect:** Automatically routes system traffic through the SOCKS proxy.
    * **On Disconnect:** Seamlessly restores your system's network settings to default (Auto) mode.
* **Cross-Platform:** Developed with PyQt5 for a consistent experience on **Windows**, **macOS**, and **Linux**.
* **User-Friendly Interface:** A clean, intuitive dashboard to switch between tunnels with a single click.

## Prerequisites

Before running the application, ensure the following are installed on your system:

* **Python 3.13.x**
* **autossh:**
    * *Linux:* `sudo apt install autossh`
    * *macOS:* `brew install autossh`
    * *Windows:* Ensure `autossh` is in your system PATH (usually via Git Bash or Cygwin).

## Installation & Usage

This project uses [uv](https://github.com/astral-sh/uv), an extremely fast Python package installer and resolver.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mortexafarhadi/ssh_tunnel_manager.git
    cd ssh_tunnel_manager
    ```

2.  **Run with `uv`:**
    You can run the application directly without manual environment setup:
    ```bash
    uv run main.py
    ```
    *If you don't have `uv` installed, you can install it via `pip install uv` or follow the instructions at [astral.sh/uv](https://astral.sh/uv).*

## How to Use

1.  **Add a Server:** Click the "Add Server" button and enter your SSH credentials.
2.  **Connect:** Select a profile from the list and click "Connect". The app establishes the SSH tunnel using `autossh`.
3.  **Proxy Activation:** The app automatically configures your OS to use the local SOCKS proxy.
4.  **Disconnect:** Click "Disconnect" to stop the tunnel and revert your network settings to their original state.

## Tech Stack

* **GUI Framework:** PyQt5
* **Networking:** SSH2 protocol
* **Stability:** autossh
* **Package Manager:** [uv](https://github.com/astral-sh/uv)

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

---
*Created by [Mortexa Farhadi](https://github.com/mortexafarhadi)*