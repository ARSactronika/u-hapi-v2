# Use a lightweight Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the audio files
COPY audio_files /app/audio_files

# Expose the port on which the app will run
EXPOSE 8080

# Run the app directly for debugging
CMD ["python", "app.py"]
