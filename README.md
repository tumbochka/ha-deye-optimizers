# Deye Cloud Optimizers for Home Assistant

[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/tumbochka/ha-deye-optimizers/actions/workflows/validate.yml/badge.svg)](https://github.com/tumbochka/ha-deye-optimizers/actions/workflows/validate.yml)

Per-panel data from **Deye panel optimizers** (SUN-XL02-B with the SUN-XL20-B concentrator) in Home Assistant.

The optimizers talk to their concentrator over the PV cables, and the concentrator uploads only to
Deye Cloud — the data is not available from the inverter, over local Modbus, or in the official
Deye Cloud OpenAPI (which only reports an online status for optimizers). This integration reads it
from the same API the [deyecloud.com](https://www.deyecloud.com) website uses.

> **Unofficial.** This uses the undocumented web API of deyecloud.com. Deye can change it at any
> time, which would break the integration until it is updated. Not affiliated with Deye.

## What you get

For every optimizer (one HA device each, linked to its concentrator):

| Entity | Unit | Notes |
|---|---|---|
| Power | W | panel input power |
| Energy today | kWh | resets daily (`total_increasing`, works with statistics) |
| Panel voltage | V | input voltage |
| Panel current | A | input current |
| Last cloud update | timestamp | diagnostic |
| Online | on/off | diagnostic |

Plus an *Online* sensor for each concentrator. All stations of the account are discovered
automatically; optimizers added later appear without a restart. Data is polled every 5 minutes,
which matches how often the concentrator uploads.

## Installation

### HACS (recommended)
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/tumbochka/ha-deye-optimizers`, category **Integration**.
2. Install **Deye Cloud Optimizers** and restart Home Assistant.

### Manual
Copy `custom_components/deye_optimizers` into your `config/custom_components/` and restart.

## Configuration

**Settings → Devices & services → Add integration → Deye Cloud Optimizers**, then enter:

- the e-mail / phone / user name and password you use on deyecloud.com or in the Deye Cloud app;
- the data center of your account: Europe (`eu1.deyecloud.com`), Americas (`us1.deyecloud.com`) or India.

The password itself is never stored: like the website, the integration keeps only its SHA-256 hash.
Access tokens (valid 60 days) are refreshed automatically; if the password changes, Home Assistant
asks you to re-authenticate.

## Dashboard example

See [`examples/dashboard.yaml`](examples/dashboard.yaml): a tile per panel (power, V · A · kWh,
and a bar comparing it with the best panel right now) and a Deye-style day chart with W / V / A / kWh
axes. It uses [button-card](https://github.com/custom-cards/button-card) and
[apexcharts-card](https://github.com/RomRider/apexcharts-card).

## Troubleshooting

- *Invalid user name or password* — check that you can log in on deyecloud.com with the same
  credentials and that the right data center is selected.
- Download diagnostics from the integration page when reporting issues; credentials, tokens,
  serial numbers and station names are redacted.
- Only the SUN-XL02-B / SUN-XL20-B combination has been tested (EU data center). Reports for other
  regions and optimizer models are welcome.

## License

MIT
