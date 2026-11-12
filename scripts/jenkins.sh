#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common.sh"
export PROJECT_DIR="$ROOT"
export JENKINS_HOME="$LAB_DIR/jenkins-home"
export XDG_CACHE_HOME="$LAB_DIR/cache"
mkdir -p "$JENKINS_HOME/init.groovy.d"
cp "$ROOT/scripts/jenkins-init.groovy" "$JENKINS_HOME/init.groovy.d/01-pipeline.groovy"
if [[ ! -s "$LAB_DIR/jenkins.war" ]]; then
  curl -fL --max-time 180 https://get.jenkins.io/war-stable/2.528.3/jenkins.war -o "$LAB_DIR/jenkins.war"
fi
if [[ ! -s "$LAB_DIR/jenkins-plugin-manager.jar" ]]; then
  curl -fL --max-time 120 https://github.com/jenkinsci/plugin-installation-manager-tool/releases/download/2.13.2/jenkins-plugin-manager-2.13.2.jar -o "$LAB_DIR/jenkins-plugin-manager.jar"
fi
JAVA=${JAVA_HOME:+$JAVA_HOME/bin/}java
"$JAVA" -jar "$LAB_DIR/jenkins-plugin-manager.jar" --war "$LAB_DIR/jenkins.war" \
  --plugin-download-directory "$JENKINS_HOME/plugins" --plugin-file "$ROOT/jenkins-plugins.txt"
exec "$JAVA" -Xms128m -Xmx512m -Djenkins.install.runSetupWizard=false -jar "$LAB_DIR/jenkins.war" \
  --httpListenAddress=127.0.0.1 --httpPort=18081 --webroot="$LAB_DIR/jenkins-webroot"
