from locust import HttpUser, task, between

class ReportUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def view_reports(self):
        self.client.get('/reportes')
