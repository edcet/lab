<<<<<<< Updated upstream
# ProxmoxHomeLabNotes

## Appunti vari sul progetto Proxmox

Il progetto Proxmox prevede di impostare un cluster di almeno tre nodi Proxmox, per far girare le seguenti istanze:

Plesk (mailserver)

- [ ] How to manage the mailserver with cloudflare

Proxmox (Hypervisor)
=======
# Neural Fabric eXtended (NFX)

High-performance neural processing framework optimized for M1 GPUs.

## Features

- Efficient memory management with GPU acceleration
- Modular process orchestration
- Clean CLI interface
- Async processing pipeline
- Metal integration for M1 optimization
>>>>>>> Stashed changes

- [x] PfSense in HA
- [x] HomeAssistant (domotica)
- [x] 3x TrueNAS SCALE cluster (filesystem) - NOT WORKING
- [x] Truecommand to manage TrueNAS SCALE gluster cluster - NOT WORKING
- [x] Gluseterfs cluster
- [x] 3x haproxy for HA implementations
- [x] 3x etcd cluster for kubernetes
- [x] 3x control planes, 3x worker nodes kubernetes cluster
  - [x] Metallb Loadbalancer
  - [x] Multus multinetwork
  - [x] Longhorn storage
  - [x] Portainer
  - [x] Certmanager
  - [x] Traefik
  - [x] Proxmox monitoring (Prometheus-Grafana)
  - [x] Proxmox Backup monitoring (Prometheus-Grafana)
  - [x] Haproxy monitoring
  - [x] Dell Idrac Monitoring
  - [x] Arista switch monitoring
  - [x] Ceph monitoring
  - [x] Glusterfs monitoring
  - [x] NFS monitoring
  - [x] Uptimekuma
  - [x] Kured
  - [x] Heimdall
  - [x] Homer
  - [x] Homepage
  - [ ] Datree (deprecated)
  - [x] Teleport
  - [x] Nvidia GPU plugin
  - [x] NFS via NFS subdir provisioner
  - [x] node feature discovery (not needed with Nvidia GPU plugin)
  - [x] reloader (?)
  - [x] k8TZ (to set a default timezone for the cluster)
  - [ ] Kyverno
  - [ ] Cilium+Hubble (?)
  - [ ] Authelia+lldap
  - [ ] CloudnativePG
  - [ ] kubelet-csr-approver
  - [ ] Livesync for Obsidian (through couchdb cluster)
  - [x] Postgresql cluster with pgadmin and monitoring
  - [x] MySQL replica cluster with Proxysql and Phpmyadmin; MySQL Prometheus-Grafana monitoring
  - [x] Mariadb replica cluster with Proxysql and Phpmyadmin; Mariadb Prometheus-Grafana monitoring
  - [x] Redis and Redis Prometheus-Grafana monitoring
  - [x] Dbgate for multi-db client
  - [x] Cloudbeaver for multi-db client
  - [x] Memcached
  - [x] MinIO for S3 ObjectStorage
  - [x] ArgoCD for CD/DI
  - [x] Gitlab for CD/CI
  - [x] Hasicorp vault and External secrets for secret SPoT
  - [x] Velero Backup
  - [x] NextCloud (FileServer) and Prometheus-Grafana monitoring
    - [x] Nextcloud apps
    - [ ] Other nextcloud apps <https://www.tecmint.com/nextcloud-apps/amp/>
  - [x] Plex (MediaServer)
    - [x] With Sonarr, Radarr, Transmission, Bazarr, Lidarr, Readarr, Prowlarr, Unpackerr, Overseer
    - [ ] Tautulli, all other "rr": autobrr, omegabrr, plex-auto-languages, plex-meta-manager, recyclarr, sabnzbd, wizarr
  - [x] VS code (code-server)
  - [ ] Boing shared computing
  - [ ] Vaultwarden <https://github.com/dani-garcia/vaultwarden/wiki/Kubernetes-deployment>
  - [ ] the lounge
  - [x] actualbudget
  - [ ] Authelia? <https://www.authelia.com/integration/kubernetes/introduction/>
  - [ ] Guacamole? <https://github.com/thomas-illiet/k8s-guacamole>
  - [ ] UrBackup (Backup)
  - [ ] miniflux
  - [ ] shlink
  - [ ] nut management
  - [ ] paperless
  - [x] Stirling PDF
  - [ ] Reactive Resume
  - [ ] Firefly III
  - [ ] Flatnotes
  - [x] IT-tools
  - [x] Drawio

<<<<<<< Updated upstream
<https://github.com/awesome-selfhosted/awesome-selfhosted>
=======
```bash
# Basic installation
pip install nfx

# With development tools
pip install nfx[dev]

# With documentation tools
pip install nfx[docs]
```

## Quick Start

1. Start the system:
```bash
nfx start
```

2. Process data:
```bash
nfx process data.npy --output results.npy
```

3. View statistics:
```bash
nfx stats
```

## Usage

### Adding Processes

Add a new process to the pipeline:
```bash
nfx add-process myprocess --priority 2 --timeout 10.0
```

### Connecting Processes

Connect processes in the pipeline:
```bash
nfx connect process1 process2
```

### Configuration

Create a JSON configuration file:
```json
{
  "compute": {
    "threads": 8,
    "batch_size": 32,
    "precision": "float32",
    "device": "auto"
  },
  "memory": {
    "pool_size": 1073741824,
    "alignment": 16
  }
}
```

Start with configuration:
```bash
nfx start -c config.json
```

## Development

1. Clone the repository:
```bash
git clone https://github.com/nfx-team/nfx.git
cd nfx
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Run tests:
```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
>>>>>>> Stashed changes
