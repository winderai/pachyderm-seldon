# Pachyderm-SeldonDeploy integration

Repository content:

- `gke_install` folder: step by step instructions to install prerequistes on a GKE cluster (public & private). This option uses the native Pachyderm deployment for GKE (requires a storage bucket).
- `minikube_install` folder: step by step instructions to install prerequistes on a Minikube cluster.
- `repo` folder:
    * `tutorial.ipynb` is the demo notebook
    * `data` datasets folder
    * `dataset-prep.ipynb` notebook to create datasets
    * various Training/Deployer folders, build them with `make build`
