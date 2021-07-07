
build:
	make -C IncomeTraining build
	make -C ExplainerTraining build
	make -C DriftTraining build
	make -C OutlierDetectorTraining build
	make -C Deployer build

push: build
	make -C IncomeTraining push
	make -C ExplainerTraining push
	make -C DriftTraining push
	make -C OutlierDetectorTraining push
	make -C Deployer push

pull:
	make -C IncomeTraining pull
	make -C ExplainerTraining pull
	make -C DriftTraining pull
	make -C OutlierDetectorTraining pull
	make -C Deployer pull