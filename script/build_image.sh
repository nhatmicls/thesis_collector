#!/usr/bin/env bash

echo "Input number to choice release version or test version"
echo "1: release"
echo "2: test"
echo "3: test alt"

read release

echo "Input number to choice image architectures"
echo "1: arm64/aarch64"
echo "2: x86_64/amd64"

read architectures

echo "Input password"
read pwds

echo "Prepare for building image"

if [[ "$release" == "1" ]]; then
    name="rpiscadapecom"
    target="--target prod"
elif [[ "$release" == "2" ]]; then
    name="rpiscadapecom_test"
    target="--target dev"
elif [[ "$release" == "3" ]]; then
    name="rpiscadapecom_test_alt"
    target="--target dev"
fi

name_file="./output/${name}.tar"
docker_path="./docker/Dockerfile"

echo ${pwds} | sudo -S rm ${name_file} 2>/dev/null|| echo

echo "Building image"

if [[ "$architectures" == "1" ]]; then
    echo "Arm64/aarch64 selected"
    docker buildx build --platform=linux/arm64/v8 -f ${docker_path} -t ${name} ${target} .
elif [[ "$architectures" == "2" ]]; then
    echo "x86_64/amd64 selected"
    docker buildx build --platform=linux/amd64 -f ${docker_path} -t ${name} ${target} .
fi

echo "Saving image as .tar file"

echo ${pwds} | sudo -S docker save ${name} > ${name_file}

echo "Done"