docker build -t dtk_tools.builder -f build_scripts/Dockerfile.builder build_scripts
docker run --rm -it -v ${PWD}:/app -w /app dtk_tools.builder bash