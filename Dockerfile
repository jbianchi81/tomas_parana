# syntax=docker/dockerfile:1
FROM ubuntu:24.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

    # Replace http with https in new-style sources file
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources && \
    # Temporarily disable certificate verification just for this step
    apt-get -o Acquire::https::Verify-Peer=false \
            -o Acquire::https::Verify-Host=false \
            update && \
    \
    # Install CA certificates securely
    apt-get -o Acquire::https::Verify-Peer=false \
            -o Acquire::https::Verify-Host=false \
        install -y --no-install-recommends ca-certificates && \
    \
    # Re-enable verification and do a clean update
    apt-get -o Acquire::https::Verify-Peer=true \
            -o Acquire::https::Verify-Host=true \
            update && \
    apt-get install -y --no-install-recommends \
        apt-transport-https  \
        wget \
        curl \
        python3 \
        python3-venv \
        python3-pip \
        python3-gdal \
        gdal-bin \
        nano \
        gpg \
        software-properties-common
        # && rm -rf /var/lib/apt/lists/*

# Add ubuntugis-unstable PPA manually via HTTPS
#RUN  echo "deb https://ppa.launchpadcontent.net/ubuntugis/ubuntugis-unstable/ubuntu noble main" > /etc/apt/sources.list.d/ubuntugis-unstable.list && \
#     echo "deb-src https://ppa.launchpadcontent.net/ubuntugis/ubuntugis-unstable/ubuntu noble main" >> /etc/apt/sources.list.d/ubuntugis-unstable.list

# Add the official Ubuntugis and GRASS stable PPAs
RUN add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable && \
    apt-get update && \
    apt-get install -y --no-install-recommends grass
#    rm -rf /var/lib/apt/lists/*

# install Python tools
RUN apt-get install -y --no-install-recommends python3-venv
RUN python3 -m venv $VIRTUAL_ENV
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Create workspace
WORKDIR /data

# Verify installation
RUN grass --version

# Verify environment
RUN python --version && pip list

WORKDIR /
COPY zonal_means.py .

CMD [ "bash" ]
