#!/bin/bash

echo "Updating natpierce core..."

# Get latest version
version=$(curl -sL "https://www.natpierce.cn/tempdir/info/version.html")
echo "Latest version: $version"

# Download URL
URL_AMD64="https://natpierce.oss-cn-beijing.aliyuncs.com/linux/natpierce-amd64-v${version}.tar.gz"

# Download and extract
curl -L -o "natpierce-amd64-v${version}.tar.gz" "$URL_AMD64"
mkdir -p bin
tar -xzf "natpierce-amd64-v${version}.tar.gz" -C bin
rm -f "natpierce-amd64-v${version}.tar.gz"
chmod +x bin/natpierce

echo "natpierce updated to version: $version"
