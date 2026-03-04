set dotenv-load := true

default:
    just -l

# run in production
run:
    DEV_MODE=false python main.py

# run in development mode
dev:
    DEV_MODE=true python main.py

# run in development mode with tunnel
[parallel]
devtunnel: tunnel dev


# open a tunnel
tunnel:
    cloudflared tunnel run --token {{env("CLOUDFLARED_TOKEN")}}
