#!/bin/bash
source loadtest.env && \
echo "Building loop.json" && \
cat > loop.json <<EOF
{
  "name": "Loop Testing",
  "plans": [

    {
      "name": "3 Servers",
      "description": "3 boxes",
      "steps": [
        {
          "name": "Test Cluster",
          "instance_count": 3,
          "instance_region": "us-east-1",
          "instance_type": "m3.large",
          "run_max_time": 300,
          "container_name": "loop/loadtest",
          "container_url": "https://s3.amazonaws.com/loads-docker-images/loop/loadtest.tar.bz2",
          "environment_data": [
            "LOOP_METRICS_STATSD_SERVER=$STATSD_HOST:$STATSD_PORT",
            "LOOP_SERVER_URL=https://loop.stage.mozaws.net:443",
            "LOOP_NB_USERS=100",
            "LOOP_DURATION=60",
            "LOOP_SP_URL=https://call.stage.mozaws.net/",
            "FXA_BROWSERID_ASSERTION=${FXA_BROWSERID_ASSERTION}"
          ],
          "dns_name": "testcluster.mozilla.org",
          "port_mapping": "8080:8090,8081:8081,3000:3000",
          "volume_mapping": "/var/log:/var/log/$RUN_ID:rw",
          "docker_series": "loop"
        }
      ]
    }
  ]
}
EOF
