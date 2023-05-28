# Use an official Python image as the base image
FROM python:3.10-alpine

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the dependencies specified in the requirements.txt file
RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/Asia/Bangkok /etc/localtime \
    && echo "Asia/Bangkok" > /etc/timezone \
    && apk del tzdata \
    && pip install --no-cache-dir -r requirements.txt

# Set the timezone environment variable
ENV TZ=Asia/Bangkok

# Define the command to run when the container starts
CMD ["python", "HW_controller.py"]