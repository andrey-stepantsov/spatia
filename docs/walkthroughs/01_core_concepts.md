# Spatia Core Concepts Walkthrough

This guide introduces the fundamental concepts of the Spatia environment, explaining how the UI reflects the underlying "Atomic" philosophy.

## 1. Hollow (The Intent)
**"Hollow"** refers to an Atom that exists only as **Intent**. It has a name and a location (Anchor), but no implementation logic yet.
-   **UI Action**: In the **Shatter Portal**, toggle the "Hollow Construct" switch.
-   **State**: Visualized as a Blue node.
-   **Purpose**: To reserve space and define interfaces before writing code.

## 2. Boundary (The Envelope)
**"Boundaries"** (technically called **Envelopes**) are spatial containers that define policy and grouping.
-   **UI Action**: Click **+ BOUNDARY** in the top toolbar.
-   **Function**: Atoms placed inside a Boundary inherit its properties (e.g., "IO Restricted", "ReadOnly").
-   **Visuals**: A translucent rectangular area that organisms can inhabit.

## 3. Tread (The Thread)
**"Treads"** (or **Threads**) are the visual connections between Atoms.
-   **Concept**: A Thread represents a dependency or a flow of data.
-   **Visuals**: An animated line connecting two Atoms.
-   **Critical Rules**: Deleting a visual thread in the UI can break the logical connection in the code (Slang A).

## 4. Summoning (The Agency)
**"Summoning"** is the act of invoking an AI Agent to implement a Hollow Atom.
-   **UI Action**: Click the **Summon** button on a Hollow (Blue) Atom.
-   **Process**: You select a model (e.g., Gemini 2.5 Flash), and the Agent writes the code to fulfill the Intent composed in the Hollow Atom.

## 5. Witness (The Verification)
**"Witnessing"** is the process of verifying an Atom's behavior in a hermetic environment.
-   **UI Action**: Click **Witness** on a Draft (Yellow) Atom.
-   **Mechanism**: The code is sent to a Docker container where it is compiled and tested.
-   **Status**: If successful, the Atom glows Purple (Witnessing) and then Green (Endorsed).

## 6. Endorsement (The Truth)
**"Endorsement"** is the final state of an Atom.
-   **Meaning**: The code has been verified by the **Witness** and approved by the **Sentinel**.
-   **Visuals**: The Atom glows Green.
-   **Implication**: This code is now considered "Truth" and is immutable until Shattered again.

## 7. Host (The Container)
**"Host"** refers to the runtime environment that executes the Atoms.
-   **Context**: In the web UI, the Browser is the Host for frontend components, while the Backend Server is the Host for Python logic.
