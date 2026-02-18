# Scripts — Operational Utilities

One-off and recurring utility scripts for managing infrastructure.  
**These are for technical operations, not day-to-day CEO use.**

## Quick Reference

| Script | Purpose | When to use |
|--------|---------|-------------|
| `final_verify.py` | End-to-end smoke test of all 7 infrastructure systems | After any infrastructure change |
| `check_health.py` | Check status of all connected services | Routine health check |

### Cloudflare (`cf_*`)
| Script | Purpose |
|--------|---------|
| `cf_run_harden.py` | Run security hardening (dry-run + optional apply) |
| `cf_run_minify_and_harden.py` | Re-apply minification + full hardening audit |
| `cf_security_low.py` | Set security level to "low" + verify |
| `cf_harden_runner.ipynb` | Interactive notebook for Cloudflare hardening |

### Discord (`discord_*`)
| Script | Purpose |
|--------|---------|
| `discord_audit.py` | Read-only audit of server settings, roles, permissions |
| `discord_setup_full.py` | Full server setup (roles, channels, permissions, onboarding) |
| `discord_setup.py` | Create permanent invite + update Short.io redirect |
| `discord_brand_channels.py` | Apply emoji prefixes and branded topics to channels |
| `discord_brand_messages.py` | Send and pin branded intro embeds in every channel |
| `discord_emojis.py` | Generate and upload branded custom emojis |
| `discord_music_bot.py` | Create Music Lounge voice channel |
| `discord_restructure.py` | **Destructive** — Delete all channels and recreate from scratch |
| `discord_fix_channels.py` | One-off fix for failed announcement channels |
| `discord_test_bot.py` | End-to-end Discord bot test |

### Other
| Script | Purpose |
|--------|---------|
| `notion_check_dbs.py` | Verify connectivity to all 26 Notion ERP databases |
| `shortio_manage.py` | Archive old Short.io links, create UTM-tagged tracking links |

## Output

Script output files are written to `output/` (git-ignored).
