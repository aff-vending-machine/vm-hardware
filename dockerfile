# Use an official Python image as the base image
FROM python:3.10-alpine

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the dependencies specified in the requirements.txt file
RUN pip install --no-cache-dir -r requirements.txt

# Define the command to run when the container starts
CMD ["python", "HW_controller.py"]