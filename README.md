# Pachyderm - Seldon Deploy integration

Repository content:

- `gke_install` folder: step by step instructions to install prerequistes on a GKE cluster (public & private). This option uses the native Pachyderm deployment for GKE (requires a storage bucket).
- `minikube_install` folder: step by step instructions to install prerequistes on a Minikube cluster.
- `repo` folder:
    * `tutorial.ipynb`: Pachyderm/Seldon integration demo
    * `data`: datasets folder
    * various Training/Deployer folders containing related Docker Images, build them with `make build`
    * various `sh` scripts, used in the demo notebook
