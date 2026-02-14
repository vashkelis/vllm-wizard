# Profile Serialization API

<cite>
**Referenced Files in This Document**
- [profile.py](file://src/vllm_wizard/render/profile.py)
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py)
- [inputs_schema.py](file://src/vllm_wizard/schemas/inputs.py)
- [outputs_schema.py](file://src/vllm_wizard/schemas/outputs.py)
- [cli.py](file://src/vllm_wizard/cli.py)
- [sample.yaml](file://examples/profiles/sample.yaml)
- [render_init.py](file://src/vllm_wizard/render/__init__.py)
- [schemas_init.py](file://src/vllm_wizard/schemas/__init__.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document provides comprehensive API documentation for the profile serialization system used in the vLLM Wizard project. The system enables persistent storage and retrieval of configuration profiles in YAML format, facilitating reproducible model serving configurations across environments. It covers the complete lifecycle of profile creation, validation, persistence, and conversion to/from planning requests.

## Project Structure
The profile serialization system spans several modules within the vLLM Wizard codebase:

```mermaid
graph TB
subgraph "Render Module"
RP["render/profile.py<br/>Profile I/O & Conversion"]
end
subgraph "Schemas Module"
SP["schemas/profile.py<br/>Profile Data Models"]
SI["schemas/inputs.py<br/>Input Data Models"]
SO["schemas/outputs.py<br/>Output Data Models"]
end
subgraph "CLI Module"
CL["cli.py<br/>Command Line Interface"]
end
subgraph "Examples"
EX["examples/profiles/sample.yaml<br/>Sample Profile"]
end
RP --> SP
RP --> SI
CL --> RP
CL --> SI
CL --> SO
EX --> RP
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L1-L173)
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py#L1-L75)
- [inputs_schema.py](file://src/vllm_wizard/schemas/inputs.py#L1-L110)
- [outputs_schema.py](file://src/vllm_wizard/schemas/outputs.py#L1-L118)
- [cli.py](file://src/vllm_wizard/cli.py#L1-L385)
- [sample.yaml](file://examples/profiles/sample.yaml#L1-L40)

**Section sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L1-L173)
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py#L1-L75)
- [inputs_schema.py](file://src/vllm_wizard/schemas/inputs.py#L1-L110)
- [outputs_schema.py](file://src/vllm_wizard/schemas/outputs.py#L1-L118)
- [cli.py](file://src/vllm_wizard/cli.py#L1-L385)
- [sample.yaml](file://examples/profiles/sample.yaml#L1-L40)

## Core Components
The profile serialization system consists of four primary components:

### Profile Data Models
The system defines a hierarchical set of Pydantic models that represent configuration profiles:

- **Profile**: Top-level container with versioning and all configuration sections
- **ProfileModel**: Model-specific configuration (id, dtype, quantization, etc.)
- **ProfileHardware**: Hardware configuration (GPU, VRAM, interconnect)
- **ProfileWorkload**: Workload characteristics (tokens, concurrency, mode)
- **ProfilePolicy**: Memory management policies (utilization, headroom, fragmentation)
- **ProfileOutputs**: Artifact emission preferences and vLLM arguments

### Profile I/O Functions
The system provides two primary functions for profile persistence:

- **save_profile()**: Serializes a Profile object to YAML format
- **load_profile()**: Deserializes YAML data back to a Profile object

### Conversion Functions
Bidirectional conversion between profiles and planning requests:

- **profile_to_request()**: Converts Profile to PlanRequest for planning
- **request_to_profile()**: Converts PlanRequest to Profile for persistence

**Section sources**
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py#L16-L75)
- [profile.py](file://src/vllm_wizard/render/profile.py#L30-L173)

## Architecture Overview
The profile serialization system follows a layered architecture with clear separation of concerns:

```mermaid
sequenceDiagram
participant CLI as "CLI Commands"
participant Render as "Profile Renderer"
participant Schema as "Pydantic Models"
participant YAML as "YAML Parser"
participant FS as "File System"
Note over CLI,FS : Profile Loading Workflow
CLI->>Render : load_profile(path)
Render->>FS : Open YAML file
FS-->>Render : YAML content
Render->>YAML : safe_load(content)
YAML-->>Render : Parsed data
Render->>Schema : Profile(**data)
Schema-->>Render : Profile object
Render-->>CLI : Profile object
Note over CLI,FS : Profile Saving Workflow
CLI->>Render : save_profile(profile, path)
Render->>Schema : profile.model_dump(mode="json")
Schema-->>Render : Dict data
Render->>YAML : dump(data)
YAML-->>Render : YAML string
Render->>FS : Write to file
FS-->>CLI : Success
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L30-L65)
- [cli.py](file://src/vllm_wizard/cli.py#L155-L213)

The architecture ensures type safety through Pydantic validation while maintaining flexibility for YAML serialization and deserialization.

**Section sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L1-L173)
- [cli.py](file://src/vllm_wizard/cli.py#L155-L213)

## Detailed Component Analysis

### Profile Data Model Hierarchy
The profile system uses a hierarchical model structure with inheritance from Pydantic's BaseModel:

```mermaid
classDiagram
class Profile {
+int profile_version
+ProfileModel model
+ProfileHardware hardware
+ProfileWorkload workload
+ProfilePolicy policy
+ProfileOutputs outputs
}
class ProfileModel {
+str id
+str revision
+DType dtype
+Quantization quantization
+KVCacheDType kv_cache_dtype
+int max_model_len
+float params_b
}
class ProfileHardware {
+str gpu_name
+int gpus
+float vram_gb
+Interconnect interconnect
+int tp_size
}
class ProfileWorkload {
+int prompt_tokens
+int gen_tokens
+int concurrency
+bool streaming
+BatchingMode mode
}
class ProfilePolicy {
+float gpu_memory_utilization
+float overhead_gb
+float fragmentation_factor
+float headroom_gb
}
class ProfileOutputs {
+str[] emit
+dict~str,Any~ vllm_args
}
Profile --> ProfileModel
Profile --> ProfileHardware
Profile --> ProfileWorkload
Profile --> ProfilePolicy
Profile --> ProfileOutputs
```

**Diagram sources**
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py#L16-L75)

### Serialization Format and Validation
The system employs Pydantic's built-in validation mechanisms combined with YAML serialization:

#### Validation Mechanisms
- **Type Validation**: Automatic type checking for all fields
- **Range Validation**: Numeric fields validated against configured bounds
- **Enum Validation**: String fields restricted to predefined enum values
- **Required Fields**: Mandatory fields enforced during construction

#### Serialization Process
The serialization process converts Pydantic models to dictionaries using JSON-compatible mode, ensuring proper enum handling:

```mermaid
flowchart TD
Start([Profile Object]) --> Dump["model_dump(mode='json')"]
Dump --> Dict["Dict with enum values"]
Dict --> YAML["yaml.dump()"]
YAML --> File["YAML File"]
File --> End([Serialized Profile])
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L37-L43)

#### Deserialization Process
Deserialization reverses the process with automatic validation:

```mermaid
flowchart TD
Start([YAML File]) --> Read["Open and read file"]
Read --> SafeLoad["yaml.safe_load()"]
SafeLoad --> Dict["Parsed Dictionary"]
Dict --> Validate["Profile(**data)"]
Validate --> End([Profile Object])
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L59-L65)

**Section sources**
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py#L16-L75)
- [profile.py](file://src/vllm_wizard/render/profile.py#L30-L65)

### Conversion Between Profiles and Requests
The system provides bidirectional conversion between profiles and planning requests:

#### Profile to Request Conversion
```mermaid
sequenceDiagram
participant Prof as "Profile"
participant Conv as "profile_to_request()"
participant Req as "PlanRequest"
participant Model as "ModelInput"
participant Hard as "HardwareInput"
participant Work as "WorkloadInput"
participant Pol as "PolicyInput"
Prof->>Conv : profile_to_request(profile)
Conv->>Model : Create ModelInput
Conv->>Hard : Create HardwareInput
Conv->>Work : Create WorkloadInput
Conv->>Pol : Create PolicyInput
Conv->>Req : Create PlanRequest
Req-->>Conv : PlanRequest object
Conv-->>Prof : PlanRequest object
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L68-L115)

#### Request to Profile Conversion
```mermaid
sequenceDiagram
participant Req as "PlanRequest"
participant Conv as "request_to_profile()"
participant Prof as "Profile"
participant PM as "ProfileModel"
participant PH as "ProfileHardware"
participant PW as "ProfileWorkload"
participant PP as "ProfilePolicy"
participant PO as "ProfileOutputs"
Req->>Conv : request_to_profile(request, emit)
Conv->>PM : Create ProfileModel
Conv->>PH : Create ProfileHardware
Conv->>PW : Create ProfileWorkload
Conv->>PP : Create ProfilePolicy
Conv->>PO : Create ProfileOutputs
Conv->>Prof : Create Profile(version=1)
Prof-->>Conv : Profile object
Conv-->>Req : Profile object
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L118-L172)

**Section sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L68-L172)

### CLI Integration and Usage Patterns
The CLI integrates profile functionality through dedicated commands:

#### Profile Loading in CLI
The CLI supports loading profiles via the `--profile` option, enabling reproducible configurations:

```mermaid
flowchart TD
CLI["vllm-wizard plan --profile file.yaml"] --> Load["load_profile(file.yaml)"]
Load --> Convert["profile_to_request()"]
Convert --> Plan["run_plan()"]
Plan --> Output["render_console_report()"]
```

**Diagram sources**
- [cli.py](file://src/vllm_wizard/cli.py#L155-L213)

#### Profile Generation in CLI
The CLI can generate profiles alongside other artifacts:

```mermaid
flowchart TD
CLI["vllm-wizard generate --emit command,profile"] --> Plan["run_plan()"]
Plan --> CreateProfile["request_to_profile()"]
CreateProfile --> Save["save_profile()"]
Save --> File["profile.yaml"]
```

**Diagram sources**
- [cli.py](file://src/vllm_wizard/cli.py#L315-L350)

**Section sources**
- [cli.py](file://src/vllm_wizard/cli.py#L155-L213)
- [cli.py](file://src/vllm_wizard/cli.py#L315-L350)

## Dependency Analysis
The profile serialization system exhibits clear dependency relationships:

```mermaid
graph TB
subgraph "External Dependencies"
PY["Pydantic"]
YML["PyYAML"]
TY["Typer"]
end
subgraph "Internal Dependencies"
RP["render/profile.py"]
SP["schemas/profile.py"]
SI["schemas/inputs.py"]
SO["schemas/outputs.py"]
CL["cli.py"]
end
RP --> SP
RP --> SI
RP --> YML
CL --> RP
CL --> SI
CL --> SO
CL --> TY
SP --> PY
SI --> PY
SO --> PY
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L1-L27)
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py#L1-L13)
- [inputs_schema.py](file://src/vllm_wizard/schemas/inputs.py#L1-L6)
- [outputs_schema.py](file://src/vllm_wizard/schemas/outputs.py#L1-L6)
- [cli.py](file://src/vllm_wizard/cli.py#L1-L33)

The system maintains loose coupling between modules while ensuring strong type safety through Pydantic models.

**Section sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L1-L27)
- [profile_schema.py](file://src/vllm_wizard/schemas/profile.py#L1-L13)
- [inputs_schema.py](file://src/vllm_wizard/schemas/inputs.py#L1-L6)
- [outputs_schema.py](file://src/vllm_wizard/schemas/outputs.py#L1-L6)
- [cli.py](file://src/vllm_wizard/cli.py#L1-L33)

## Performance Considerations
The profile serialization system is designed for efficiency and reliability:

### Serialization Performance
- **JSON Mode Dumping**: Using `mode="json"` ensures efficient serialization of enum values
- **Minimal Memory Footprint**: Profiles are lightweight compared to model configurations
- **Lazy Loading**: Profiles are loaded only when needed via CLI commands

### Validation Performance
- **Compile-time Validation**: Pydantic validation occurs during object construction
- **Early Error Detection**: Invalid profiles are caught immediately during deserialization
- **Type Coercion**: Automatic type coercion reduces manual validation overhead

### File I/O Performance
- **Atomic Writes**: Profile writes occur atomically through file writing operations
- **Directory Creation**: Automatic directory creation prevents race conditions
- **Stream Processing**: YAML parsing uses streaming for large profiles

## Troubleshooting Guide

### Common Error Scenarios

#### File Not Found Errors
**Symptoms**: `FileNotFoundError` when loading profiles
**Causes**: Non-existent profile file paths
**Solutions**: Verify file existence and correct path specification

#### Validation Errors
**Symptoms**: `ValueError` during profile loading
**Causes**: Invalid field types, out-of-range values, or missing required fields
**Solutions**: 
- Check YAML syntax validity
- Validate field types match expected enums
- Ensure numeric fields meet validation constraints

#### Type Conversion Issues
**Symptoms**: Unexpected type errors during serialization
**Causes**: Mixed type usage in profile data
**Solutions**: 
- Use consistent enum values
- Ensure numeric fields are properly formatted
- Validate boolean values are correctly specified

### Error Handling Implementation
The system implements robust error handling:

```mermaid
flowchart TD
Start([Profile Operation]) --> Try["Try Operation"]
Try --> Success{"Operation Success?"}
Success --> |Yes| Return["Return Result"]
Success --> |No| Catch["Catch Exception"]
Catch --> TypeCheck{"Exception Type?"}
TypeCheck --> |FileNotFoundError| FileErr["Handle File Error"]
TypeCheck --> |ValueError| ValErr["Handle Validation Error"]
TypeCheck --> |Other| GenErr["Handle Generic Error"]
FileErr --> Log["Log Error Message"]
ValErr --> Log
GenErr --> Log
Log --> Exit([Exit with Error Code])
```

**Diagram sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L55-L65)
- [cli.py](file://src/vllm_wizard/cli.py#L204-L212)

**Section sources**
- [profile.py](file://src/vllm_wizard/render/profile.py#L46-L65)
- [cli.py](file://src/vllm_wizard/cli.py#L204-L212)

## Conclusion
The vLLM Wizard profile serialization system provides a robust, type-safe mechanism for persisting and sharing configuration profiles. Its architecture ensures:

- **Type Safety**: Comprehensive validation through Pydantic models
- **Flexibility**: Human-readable YAML format with programmatic access
- **Reproducibility**: Versioned profiles enable consistent deployments
- **Integration**: Seamless CLI integration for practical usage

The system's design supports both development workflows and production deployment scenarios, making it an essential component of the vLLM Wizard ecosystem.