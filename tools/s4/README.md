https://github.com/rh-aiservices-bu/s4

# Run S4 with persistent storage
podman run -d \
  --name s4 \
  -p 5000:5000 \
  -p 7480:7480 \
  -v s4-data:/var/lib/ceph/radosgw \
  quay.io/rh-aiservices-bu/s4:latest

# Access the web UI
open http://localhost:5000

# Use S3 API with default credentials
export AWS_ACCESS_KEY_ID=s4admin
export AWS_SECRET_ACCESS_KEY=s4secret
export AWS_ENDPOINT_URL=http://localhost:7480
aws s3 mb s3://my-bucket


