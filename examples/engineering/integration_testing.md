# Few-Shot Example: Integration Testing Strategy

**Domain:** engineering
**Skill Level:** Intermediate
**Pattern:** Analyze → Design → Implement → Verify

---

## User Query

We have a microservices architecture with these services:
- User Service (PostgreSQL)
- Order Service (PostgreSQL)
- Payment Service (Stripe API)
- Notification Service (SendGrid API)

Order flow: User → Order → Payment → Notification

How do I design integration tests that are reliable and don't hit real external APIs?

---

## Exemplary Response

### 1. Integration Testing Pyramid

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TESTING PYRAMID FOR MICROSERVICES                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                            ▲                                                 │
│                           ╱ ╲        E2E Tests (5%)                         │
│                          ╱   ╲       Real environment, full flow            │
│                         ╱─────╲                                              │
│                        ╱       ╲                                             │
│                       ╱ Contract ╲   Contract Tests (15%)                   │
│                      ╱   Tests    ╲  API compatibility verification         │
│                     ╱─────────────╲                                          │
│                    ╱               ╲                                         │
│                   ╱  Integration    ╲  Integration Tests (30%)              │
│                  ╱     Tests         ╲ Service + dependencies               │
│                 ╱─────────────────────╲                                      │
│                ╱                       ╲                                     │
│               ╱      Unit Tests         ╲  Unit Tests (50%)                 │
│              ╱                           ╲ Isolated business logic          │
│             ╱─────────────────────────────╲                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Test Isolation Strategies

| External Dependency | Strategy | Tool | Speed | Fidelity |
|---------------------|----------|------|-------|----------|
| PostgreSQL | Testcontainers | testcontainers-python | Medium | High |
| Other Microservices | Mocks/Stubs | responses, httpretty | Fast | Medium |
| Stripe API | WireMock/VCR | wiremock, vcrpy | Fast | High |
| SendGrid API | Fake Server | fakesmtp, mailtrap | Fast | Medium |
| Message Queue | Embedded | embedded-kafka | Medium | High |

### 3. Test Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTEGRATION TEST ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TEST RUNNER                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │   FIXTURES (pytest)                                                  │    │
│  │   ├── db_session (PostgreSQL via Testcontainers)                    │    │
│  │   ├── stripe_mock (WireMock container)                              │    │
│  │   ├── user_service (real service, test DB)                          │    │
│  │   └── order_service (real service, mocked deps)                     │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │   SERVICE UNDER TEST                                                 │    │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │    │
│  │   │ Order Service│───►│ Payment Stub │───►│  Notif Stub  │          │    │
│  │   └──────────────┘    └──────────────┘    └──────────────┘          │    │
│  │          │                                                           │    │
│  │          ▼                                                           │    │
│  │   ┌──────────────┐                                                   │    │
│  │   │  PostgreSQL  │  (Testcontainers)                                │    │
│  │   └──────────────┘                                                   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Implementation

#### 4.1 Project Structure

```
tests/
├── conftest.py              # Shared fixtures
├── integration/
│   ├── __init__.py
│   ├── conftest.py          # Integration-specific fixtures
│   ├── test_order_flow.py   # Order creation flow
│   ├── test_payment_flow.py # Payment processing
│   └── test_user_orders.py  # User-Order relationship
├── contract/
│   ├── test_order_api.py    # API contract tests
│   └── test_payment_api.py
├── mocks/
│   ├── stripe_responses.py  # Stripe API mock responses
│   └── sendgrid_responses.py
└── fixtures/
    ├── users.json           # Test data
    └── orders.json
```

#### 4.2 Testcontainers Setup

```python
# tests/integration/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.core.waiting_utils import wait_for_logs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Shared PostgreSQL container for all integration tests
@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container once per test session."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        # Wait for container to be ready
        wait_for_logs(postgres, "database system is ready to accept connections")
        yield postgres


@pytest.fixture(scope="session")
def db_engine(postgres_container):
    """Create SQLAlchemy engine connected to test database."""
    engine = create_engine(postgres_container.get_connection_url())

    # Create all tables
    from app.models import Base
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()

    yield session

    # Rollback any uncommitted changes
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def clean_db(db_session):
    """Clean all tables before each test."""
    # Delete in reverse dependency order
    db_session.execute("TRUNCATE orders, users CASCADE")
    db_session.commit()
    yield db_session
```

#### 4.3 External API Mocking with WireMock

```python
# tests/integration/conftest.py
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
import requests


@pytest.fixture(scope="session")
def wiremock_container():
    """WireMock container for Stripe API mocking."""
    container = DockerContainer("wiremock/wiremock:2.35.0")
    container.with_exposed_ports(8080)
    container.with_command("--verbose")

    with container:
        wait_for_logs(container, "verbose:")
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8080)
        base_url = f"http://{host}:{port}"
        yield base_url


@pytest.fixture(scope="function")
def stripe_mock(wiremock_container):
    """Configure Stripe mock responses for each test."""
    class StripeMock:
        def __init__(self, base_url):
            self.base_url = base_url
            self.admin_url = f"{base_url}/__admin"

        def stub_successful_charge(self, amount: int, charge_id: str = "ch_test123"):
            """Mock successful Stripe charge."""
            requests.post(f"{self.admin_url}/mappings", json={
                "request": {
                    "method": "POST",
                    "urlPath": "/v1/charges"
                },
                "response": {
                    "status": 200,
                    "jsonBody": {
                        "id": charge_id,
                        "amount": amount,
                        "currency": "usd",
                        "status": "succeeded",
                        "paid": True
                    },
                    "headers": {
                        "Content-Type": "application/json"
                    }
                }
            })

        def stub_declined_card(self):
            """Mock declined card response."""
            requests.post(f"{self.admin_url}/mappings", json={
                "request": {
                    "method": "POST",
                    "urlPath": "/v1/charges"
                },
                "response": {
                    "status": 402,
                    "jsonBody": {
                        "error": {
                            "type": "card_error",
                            "code": "card_declined",
                            "message": "Your card was declined."
                        }
                    }
                }
            })

        def reset(self):
            """Clear all stubs."""
            requests.post(f"{self.admin_url}/reset")

    mock = StripeMock(wiremock_container)
    yield mock
    mock.reset()
```

#### 4.4 Integration Test Examples

```python
# tests/integration/test_order_flow.py
import pytest
from decimal import Decimal
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.models import User, Order, OrderStatus


class TestOrderCreationFlow:
    """Integration tests for complete order creation flow."""

    @pytest.fixture
    def order_service(self, db_session, stripe_mock, wiremock_container):
        """Order service with mocked payment."""
        payment_service = PaymentService(
            stripe_api_url=wiremock_container  # Point to WireMock
        )
        return OrderService(
            db_session=db_session,
            payment_service=payment_service
        )

    @pytest.fixture
    def test_user(self, clean_db):
        """Create test user."""
        user = User(
            email="test@example.com",
            name="Test User"
        )
        clean_db.add(user)
        clean_db.commit()
        return user

    def test_create_order_success(self, order_service, test_user, stripe_mock):
        """Test successful order creation with payment."""
        # Arrange
        stripe_mock.stub_successful_charge(amount=5000)
        order_data = {
            "user_id": test_user.id,
            "items": [
                {"product_id": "prod_123", "quantity": 2, "price": 25.00}
            ],
            "payment_method": "pm_card_visa"
        }

        # Act
        order = order_service.create_order(order_data)

        # Assert
        assert order.id is not None
        assert order.status == OrderStatus.PAID
        assert order.total == Decimal("50.00")
        assert order.user_id == test_user.id
        assert order.payment_id == "ch_test123"

    def test_create_order_payment_declined(self, order_service, test_user, stripe_mock):
        """Test order creation with declined payment."""
        # Arrange
        stripe_mock.stub_declined_card()
        order_data = {
            "user_id": test_user.id,
            "items": [{"product_id": "prod_123", "quantity": 1, "price": 100.00}],
            "payment_method": "pm_card_declined"
        }

        # Act & Assert
        with pytest.raises(PaymentDeclinedException) as exc_info:
            order_service.create_order(order_data)

        assert "card_declined" in str(exc_info.value)

        # Verify order was NOT created
        orders = order_service.get_user_orders(test_user.id)
        assert len(orders) == 0

    def test_create_order_rollback_on_notification_failure(
        self, order_service, test_user, stripe_mock, notification_mock
    ):
        """Test transaction rollback when notification fails."""
        # Arrange
        stripe_mock.stub_successful_charge(amount=5000)
        notification_mock.stub_failure()  # Notification will fail

        order_data = {
            "user_id": test_user.id,
            "items": [{"product_id": "prod_123", "quantity": 2, "price": 25.00}],
            "payment_method": "pm_card_visa"
        }

        # Act
        # Depending on business logic, this might:
        # A) Fail and rollback payment
        # B) Succeed but log notification failure
        order = order_service.create_order(order_data)

        # Assert (assuming option B - notification is non-critical)
        assert order.status == OrderStatus.PAID
        assert order.notification_sent == False
        # Check that retry was scheduled
        assert order.notification_retry_at is not None
```

#### 4.5 VCR.py for Recording Real API Responses

```python
# tests/integration/test_payment_flow.py
import pytest
import vcr
from app.services.payment_service import PaymentService

# VCR configuration
my_vcr = vcr.VCR(
    cassette_library_dir='tests/fixtures/cassettes',
    record_mode='none',  # 'new_episodes' to record, 'none' to playback only
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query'],
    filter_headers=['Authorization'],  # Don't record API keys
    filter_post_data_parameters=['card[number]', 'card[cvc]']
)


class TestStripeIntegration:
    """Tests using recorded Stripe API responses."""

    @my_vcr.use_cassette('stripe_charge_success.yaml')
    def test_charge_card_success(self):
        """Test successful charge with recorded response."""
        service = PaymentService()

        result = service.charge(
            amount=5000,
            currency='usd',
            source='tok_visa',
            description='Test charge'
        )

        assert result['status'] == 'succeeded'
        assert result['amount'] == 5000

    @my_vcr.use_cassette('stripe_charge_declined.yaml')
    def test_charge_card_declined(self):
        """Test declined card with recorded response."""
        service = PaymentService()

        with pytest.raises(PaymentDeclinedException):
            service.charge(
                amount=5000,
                currency='usd',
                source='tok_chargeDeclined',
                description='Test decline'
            )
```

#### 4.6 Contract Testing with Pact

```python
# tests/contract/test_order_api_contract.py
import pytest
from pact import Consumer, Provider, Like, EachLike, Term

# Define consumer expectations
pact = Consumer('OrderService').has_pact_with(
    Provider('PaymentService'),
    pact_dir='./pacts'
)


class TestOrderPaymentContract:
    """Contract tests between Order and Payment services."""

    def test_create_charge_contract(self):
        """Verify Payment Service accepts charge requests."""
        expected_response = {
            "id": Like("ch_123"),
            "amount": 5000,
            "currency": "usd",
            "status": Term(r"succeeded|pending|failed", "succeeded"),
            "metadata": Like({})
        }

        (pact
            .given("Payment service is available")
            .upon_receiving("a charge request")
            .with_request(
                method="POST",
                path="/v1/charges",
                headers={"Content-Type": "application/json"},
                body={
                    "amount": 5000,
                    "currency": "usd",
                    "source": Like("tok_visa")
                }
            )
            .will_respond_with(200, body=expected_response))

        with pact:
            # Make actual call to mock server
            result = PaymentClient(pact.uri).create_charge(
                amount=5000,
                currency="usd",
                source="tok_visa"
            )

            assert result["status"] == "succeeded"
```

### 5. Test Execution Strategy

#### 5.1 Pytest Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (require containers)
    contract: Contract tests
    e2e: End-to-end tests (slow, full environment)
    slow: Tests that take > 5 seconds

# Default: run unit and integration, skip e2e
addopts = -v --tb=short -m "not e2e"

# Parallel execution
# addopts = -v --tb=short -n auto
```

#### 5.2 CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-test.txt
      - run: pytest tests/ -m "unit" --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:dind
        options: --privileged
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-test.txt
      - run: pytest tests/integration/ -m "integration" --tb=long
        env:
          DOCKER_HOST: unix:///var/run/docker.sock

  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-test.txt
      - run: pytest tests/contract/ -m "contract"
      - name: Publish Pacts
        run: |
          pact-broker publish ./pacts \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --consumer-app-version=${{ github.sha }}
```

### 6. Best Practices Summary

| Practice | Rationale |
|----------|-----------|
| Use Testcontainers for databases | Real DB behavior, isolated per test session |
| WireMock for external APIs | Predictable responses, no API rate limits |
| VCR.py for recording | Capture real responses once, replay forever |
| Contract tests for inter-service | Catch breaking changes early |
| Function-scoped fixtures | Test isolation, clean state |
| Session-scoped containers | Speed (don't restart containers per test) |
| Parallel execution | Faster CI feedback |
| Separate test marks | Run appropriate tests in appropriate contexts |

### 7. Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Tests depend on execution order | Use fixtures, clean state per test |
| Flaky tests due to timing | Use explicit waits, not sleep() |
| Tests hit real APIs | Configure test environment properly |
| Slow container startup | Use session-scoped containers |
| Port conflicts | Let Testcontainers pick random ports |
| Data pollution | Truncate tables in fixture, use transactions |

---

## Why This Is A Good Example

- Clear testing pyramid with percentage guidelines
- Multiple mocking strategies with trade-offs
- Complete code examples (fixtures, tests, CI)
- Addresses real microservices challenges
- Includes contract testing

---

## Key Patterns

1. **Test Isolation** - Each test gets clean state
2. **Container-Based Testing** - Real dependencies, isolated environment
3. **API Mocking Layers** - WireMock for HTTP, VCR for recording
4. **Contract-First** - Verify API compatibility between services

---

**Tags:** #engineering #testing #integration #microservices #testcontainers #pytest
**Version:** 1.0.0
**Last Updated:** 2026-01-23
