import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition

// Exclusivo do processo didatico sem autenticacao, ligado apenas em loopback.
def jenkins = Jenkins.get()
jenkins.setNumExecutors(1)
jenkins.setSystemMessage('Laboratorio local isolado: Pipeline final DevOps')
def job = jenkins.getItem('pipeline-final')
if (job == null) job = jenkins.createProject(WorkflowJob, 'pipeline-final')
job.setDefinition(new CpsFlowDefinition(new File(System.getenv('PROJECT_DIR'), 'Jenkinsfile').text, true))
job.setDescription('Testes -> Docker -> registry local -> Helm/Kind -> Filebeat -> Kibana. Fonte: commit local.')
job.save()
jenkins.save()
