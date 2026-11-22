# System Diagrams – Sales and Inventory Management System

## 1. Use Case Diagram

```mermaid
flowchart LR
    A[Administrator]
    C[Cashier]
    I[Inventory Clerk]

    subgraph System[Sales and Inventory]
        Login([Sign in and view stock])
        Sale([Post sale and print receipt])
        Purchase([Receive purchase and print stock-in record])
        Adjust([Record stock correction])
        Catalog([Maintain catalog and suppliers])
        Report([Run reports and export])
        Accounts([Manage accounts and expenses])
    end

    A --- Login
    A --- Sale
    A --- Purchase
    A --- Adjust
    A --- Catalog
    A --- Report
    A --- Accounts

    C --- Login
    C --- Sale

    I --- Login
    I --- Purchase
    I --- Adjust
    I --- Catalog
```

## 2. Level 1 Data Flow Diagram

```mermaid
flowchart LR
    S[Store staff] -->|Credentials| A([1 Authenticate])
    U[(Users and roles)] --> A
    A -->|Session| S

    S -->|Catalog changes| M([2 Maintain catalog])
    M -->|Catalog rows| P[(Products, categories, suppliers)]

    S -->|Sale, receipt of goods, or correction| T([3 Post movement])
    P -->|Price, cost, available stock| T
    T -->|Updated balance| P
    T -->|Header and item lines| L[(Transaction history)]
    T -->|Receipt or stock-in record| S

    X[Administrator] -->|Date, category, export format| R([4 Generate reports])
    P --> R
    L --> R
    E[(Operating expenses)] --> R
    R -->|On-screen report, PDF, or Excel| X
```

## 3. Sales Activity Diagram

```mermaid
flowchart TD
    A([Start]) --> B[Sign in]
    B --> C[Enter items tax and payment]
    C --> D{Input and role valid?}

    D -->|No| C
    D -->|Yes| E[Begin database transaction]

    E --> F{Already posted?}
    F -->|Yes| R[Show existing receipt]
    F -->|No| G[Lock product rows]

    G --> H{Stock and payment sufficient?}
    H -->|No| I[Roll back and show error]
    I --> C

    H -->|Yes| J[Save header lines and stock]
    J --> K[Commit]
    K --> R
    R --> Z([End])
```

## 4. Purchasing Activity Diagram

```mermaid
flowchart TD
    A([Start]) --> B[Clerk signs in]
    B --> C[Enter supplier received items and costs]
    C --> D{Input valid?}

    D -->|No| C
    D -->|Yes| E[Begin database transaction]

    E --> F{Already posted?}
    F -->|Yes| R[Show stock-in record]
    F -->|No| G[Lock product rows]

    G --> H{Products active?}
    H -->|No| I[Roll back and show error]
    I --> C

    H -->|Yes| J[Update average cost and stock]
    J --> K[Save header and item lines]
    K --> L[Commit]
    L --> R
    R --> Z([End])
```

## 5. Diagram Explanation

The use case diagram presents the responsibilities of the Administrator, Cashier, and Inventory Clerk.

The Level 1 data flow diagram illustrates how staff interact with authentication, catalog management, transaction posting, and reporting processes.

The sales activity diagram shows the validation, stock checking, transaction processing, and receipt generation steps when posting a sale.

The purchasing activity diagram shows the process of receiving goods, validating products, updating stock and average cost, and recording the purchase transaction.