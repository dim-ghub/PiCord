# PiCord

A modular Discord automation bot for user accounts (discord.py-self), with AutoBoat as the first feature.

## 📚 Table of Contents

- [Apps](#-apps)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

## 🎁 Apps

- **Modular Architecture**: Easy to add new apps as separate modules
- **Command System**: Use prefix commands to control apps (e.g., `!start autoboat`)
- **Raspberry Pi Optimized**: Special optimizations for Raspberry Pi hardware
- **AutoBoat Integration**: Automated UnbelievaBoat bot control

## 💻 Installation

### Quick Setup (Recommended)

1. Clone the repository:

    ```bash
    git clone <repository-url>
    cd PiCord
    ```

2. Run the setup script:

    ```bash
    ./run.sh
    ```

3. The script will set up the bot and ask for your Discord token.

### Manual Setup

1. Create virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Configure your bot:
    - Copy `bot_config.json.example` to `bot_config.json`
    - Set up your `.env` file with Discord token
    - Configure AutoBoat in `apps/autoboat/config.json`

## 🚀 Usage

### Starting the Bot

```bash
./run.sh
```

### Bot Commands

- `!help` - Show available commands and apps
- `!start autoboat` - Start the AutoBoat app
- `!stop autoboat` - Stop the AutoBoat app
- `!start <app>` - Start any available app
- `!stop <app>` - Stop any running app

## ⚙️ Configuration

### Main Bot Configuration (`bot_config.json`)

```json
{
  "bot": {
    "prefix": ".pc ",
    "name": "PiCord",
    "version": "1.0.0"
  },
  "discord": {
    "token_file": ".env",
    "status": {
      "type": "idle",
      "afk": true
    }
  },
  "apps": {
    "autoboat": {
      "enabled": true,
      "config_file": "apps/autoboat/config.json"
    }
  }
}
```

### AutoBoat Configuration (`apps/autoboat/config.json`)

Configure your UnbelievaBoat automation settings:

```json
{
  "discord": {
    "channel_id": 123456789012345678
  },
  "bot": {
    "prefix": "/"
  },
  "commands": {
    "work": {
      "command": "work",
      "cooldown_minutes": 5,
      "slash_command_id": null
    },
    "collect": {
      "enabled": true,
      "command": "collect",
      "cooldown_minutes": 60,
      "slash_command_id": null
    },
    "deposit": {
      "command": "deposit",
      "slash_command_id": null
    }
  },
  "timing": {
    "response_wait_seconds": 3,
    "deposit_wait_seconds": 2,
    "startup_countdown_seconds": 5
  }
}
```

## 🍓 Raspberry Pi Optimizations

This bot includes special optimizations for Raspberry Pi:

- Memory-efficient task management
- Optimized dependency installation
- Hardware detection and tuning
- Reduced CPU usage during idle periods

## 🤝 Contributing

Contributions, issues, and feature requests welcome! Feel free to check [issues page](issues).

## 📝 License

This project is [MIT](LICENSE) licensed.

## Disclaimer

> This bot was created for educational purposes only. The developers and contributors do not take any responsibility for your Discord account. ⚠️

**Enjoy!** 🎉