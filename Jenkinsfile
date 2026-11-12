node {
    if (!env.PROJECT_DIR || !env.LAB_DIR) {
        error('Defina PROJECT_DIR e LAB_DIR no processo Jenkins isolado')
    }
    stage('Fonte versionada') {
        sh 'mkdir -p source; git -C "$PROJECT_DIR" archive HEAD | tar -C source -xf -'
    }
    dir('source') {
        def revision = sh(script: 'git -C "$PROJECT_DIR" rev-parse --short=12 HEAD', returnStdout: true).trim()
        withEnv(["TAG=${revision}-${env.BUILD_NUMBER}"]) {
            stage('Testes e Helm') { sh 'bash scripts/pipeline.sh test' }
            stage('Build Docker') { sh 'bash scripts/pipeline.sh build' }
            stage('Push registry local') { sh 'bash scripts/pipeline.sh push' }
            stage('CD Kubernetes') { sh 'bash scripts/pipeline.sh deploy' }
            stage('E2E e Filebeat') { sh 'bash scripts/pipeline.sh verify' }
            stage('Dashboard Kibana') { sh 'python3 scripts/dashboard.py' }
        }
    }
}
