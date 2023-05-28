
# build amd64
docker build --platform linux/amd64 -f dockerfile -t vm-hardware:0.0.0 .

#build arm64
docker build --platform linux/arm64 -f dockerfile -t vm-hardware:0.0.0-arm64 .

# test
docker run -it vm-hardware:0.0.0