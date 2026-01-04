#!/usr/bin/env python3
import secrets
from pathlib import Path


def get_input(prompt, default=None):
    if default:
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else default
    return input(f"{prompt}: ").strip()


def main():
    print("\n🛠️  Bookmarks Service Configuration Wizard\n")

    # Use XDG-style config directory
    config_dir = Path.home() / ".config" / "bookmarks"
    env_file = config_dir / ".env"

    if not config_dir.exists():
        print(f"📂 Creating config directory: {config_dir}")
        config_dir.mkdir(parents=True)

    if env_file.exists():
        confirm = input("⚠️  .env already exists. Overwrite? (y/N): ").lower()
        if confirm != "y":
            print("Aborted.")
            return

    # Basic Settings
    port = get_input("Server Port", "5000")
    secret_key = secrets.token_hex(24)

    # LLM Settings
    print("\n--- LLM API Keys (Optional, leave blank to skip) ---")
    perplexity_key = get_input("Perplexity API Key")
    openai_key = get_input("OpenAI API Key")
    anthropic_key = get_input("Anthropic API Key")

    # Provider Preference
    provider = "perplexity"
    if any([perplexity_key, openai_key, anthropic_key]):
        providers = []
        if perplexity_key:
            providers.append("perplexity")
        if openai_key:
            providers.append("openai")
        if anthropic_key:
            providers.append("anthropic")

        if len(providers) > 1:
            print(f"\nMultiple providers available: {', '.join(providers)}")
            provider = get_input("Default Provider", providers[0])
        elif len(providers) == 1:
            provider = providers[0]

    # Write .env
    with open(env_file, "w") as f:
        f.write("# Bookmarks Application Configuration (Generated)\n\n")
        f.write(f"BOOKMARKS_PORT={port}\n")
        f.write(f"BOOKMARKS_SECRET_KEY={secret_key}\n")
        f.write("BOOKMARKS_DATA_DIR=/data\n")
        f.write("BOOKMARKS_DEBUG=false\n\n")

        f.write("# LLM Settings\n")
        f.write(f"BOOKMARKS_LLM_PROVIDER={provider}\n")
        f.write(f"PERPLEXITY_API_KEY={perplexity_key}\n")
        f.write(f"OPENAI_API_KEY={openai_key}\n")
        f.write(f"ANTHROPIC_API_KEY={anthropic_key}\n")

    print(f"\n✅ Configuration saved to {env_file}")
    print("🚀 You can now run 'make service-install' to start the app.")


if __name__ == "__main__":
    main()
