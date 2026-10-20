---
title: 'Exercise 5: Create a Job Worker'
layout: 'section'
weight: 50

menu:
  main:
    identifier: 'Exercise 5 java'
---

### Goal

Setup a job worker and add implementations for all service tasks.

### Detailed Steps with Java Springboot

1. Clone / download the following Springboot project: https://github.com/camunda-academy/c8-platform-developers-lab-spring
2. Have a look at the documentation of the Spring Zeebe Client you are going to use:
   https://docs.camunda.io/docs/apis-tools/spring-zeebe-sdk/getting-started/
3. The Zeebe client is already available in the maven project, you can update the version in the pom.xml (check the documentation to get the latest one):

```xml
<dependency>
      <groupId>io.camunda</groupId>
      <artifactId>spring-boot-starter-camunda-sdk</artifactId>
      <version>8.y.z</version>
</dependency>
```

1. Configure Camunda Platform 8 Saas Connection:

Create/Update `src/main/resources/application.properties` creating the following entries, based on the client credentials retrieved for the previous exercise.

```properties
zeebe.client.cloud.cluster-id=xxx
zeebe.client.cloud.client-id=xxx
zeebe.client.cloud.client-secret=xxx
zeebe.client.cloud.region=bru-2
```

1. Create a new package where to place your workers: `com.camunda.academy.workers`
2. Create a `CreditCardChargingWorker`java class on the newly created package.
3. In the class, create a method to deduct the customer credit: handleCreditCardCharging
4. Annotate the method with

```java
@JobWorker(type = "credit-card-charging", autoComplete = false)
```

8. At the moment we just log something to the console and complete the task.

{{< snippet CreditCardChargingWorker-Solution >}}

@Component
public class CreditCardChargingWorker {

Logger LOGGER = LoggerFactory.getLogger(CreditCardChargingWorker.class);

@JobWorker(type = "credit-card-charging", autoComplete = false)
public void handleCreditCardCharging(final JobClient jobClient, final ActivatedJob job) {
LOGGER.info("Task definition type: " + job.getType());
jobClient.newCompleteCommand(job).send().exceptionally( throwable -> { throw new RuntimeException("Could not complete job " + job, throwable); });
}
}

{{< /snippet >}}

9.  Create another class `CreditDeductionWorker` with a worker method for managing the charge credit card worker. We'll just log the job type, we'll improve it later.

{{< snippet CreditDeductionWorker-Solution >}}

@Component
public class CreditDeductionWorker {

Logger LOGGER = LoggerFactory.getLogger(CreditDeductionWorker.class);

@JobWorker(type = "credit-deduction", autoComplete = false)
public void handleCreditDeduction(final JobClient jobClient, final ActivatedJob job) {
LOGGER.info("Task definition type: " + job.getType());
jobClient.newCompleteCommand(job).send().exceptionally( throwable -> { throw new RuntimeException("Could not complete job " + job, throwable); });
}
}

{{< /snippet >}}

1.  Run the springboot application

2.  Use the `Web Modeler` to start a new process instance with the required variables, for instance:

```
{"orderTotal": 45.99, "customerCredit": 30}
```

13. Switch to your IDE and check the console output of your job worker.

14. Open Operate and inspect the status of your process.

15. Implement handlers for the remaining service tasks. Add a console output just like the first handler.

16. Restart the workers in your IDE.

17. Find the console log of the other task(s).

18. Check the history of the process instance. How long did it take to complete this instance?
