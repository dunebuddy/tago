🇧🇷 Português | [🇺🇸 English](README.en.md)

# 🏷️ Tago

**Tago** é um CLI para padronizar tags em recursos AWS com base em **templates** e **overrides JSON**.

Ele ajuda equipes a manter **ownership**, **ambiente** e **metadados de conformidade** consistentes
entre serviços AWS, permitindo ajustes pontuais por recurso quando necessário.

O projeto é intencionalmente simples:
você fornece um template de tags, opcionalmente sobrescreve valores,
e o Tago **aplica** (ou apenas **simula**) o estado final das tags nos recursos suportados.

> ⚠️ **Aviso importante**  
> O Tago **ainda não possui uma versão estável publicada** e **não é distribuído via PyPI**.  
> Interfaces, comportamento e estrutura interna podem mudar a qualquer momento.

---

## ✨ Por que usar o Tago

- Mantém tags AWS consistentes entre serviços, sem duplicar lógica
- Permite visualizar o estado final antes de aplicar mudanças (*dry-run*)
- Usa um template único com pequenos overrides por ambiente ou recurso
- Extensível via *adapters* para suportar novos serviços AWS

---

## 📦 Instalação

O Tago deve ser instalado a partir do **código-fonte**.

### Opção recomendada: instalação local (via `uv tool`)

Essa é a forma recomendada enquanto o projeto não possui releases estáveis.

```bash
git clone https://github.com/dunebuddy/tago.git
cd tago
uv tool install .
```

> 💡 Isso instala o Tago como uma ferramenta isolada, sem poluir o ambiente global.

---

### Instalação local usando `pipx` (alternativa)

```bash
git clone https://github.com/dunebuddy/tago.git
cd tago
pipx install .
```

---

### Instalação direta a partir do GitHub (sem clonar)

Útil para testes rápidos ou ambientes descartáveis.

Usando `uv tool`:

```bash
uv tool install git+https://github.com/dunebuddy/tago.git
```

Ou usando `pipx`:

```bash
pipx install git+https://github.com/dunebuddy/tago.git
```

---

## 🚀 Início rápido

### 1️⃣ Prepare um template de tags (YAML)

```yaml
defaults:
  Owner: team-platform
  CostCenter: 1234
dynamic:
  Environment: dev
```

### 2️⃣ Aplique tags em um recurso

```bash
tago tag \
  --arn arn:aws:s3:::my-bucket \
  --template ./template.yaml
```

### 3️⃣ Simule as mudanças (sem aplicar)

```bash
tago tag \
  --arn arn:aws:s3:::my-bucket \
  --template ./template.yaml \
  --dry-run
```

---

## 🧩 Templates de tags

Os templates definem o **conjunto padrão de tags** que deve ser aplicado aos recursos.
Eles são escritos em YAML e representam a **fonte de verdade** para padronização no Tago.

Um template é dividido em duas seções explícitas:

- `defaults`: tags **fixas**, que **não podem ser sobrescritas**
- `dynamic`: tags **dinâmicas**, que **podem ser sobrescritas via `--overrides`**

Essa separação é intencional e garante que tags críticas de governança
não sejam alteradas acidentalmente.

---

### Estrutura de um template

Exemplo de template completo:

```yaml
defaults:
  Project: "vision-analytics"
  Owner: "data-platform"
  CostCenter: "CC-4022"
  Department: "advanced-analytics"
  BusinessUnit: "ai"
  Usage: "machine-learning"

dynamic:
  Environment: "{{ environment }}"
  ServiceType: "{{ service_type }}"
```
Nesse exemplo:
- Todas as tags em defaults são obrigatórias e imutáveis
- Apenas as tags em dynamic podem receber valores diferentes por recurso
- Os placeholders ({{ ... }}) indicam valores resolvidos em tempo de execução

---

### Tags fixas (defaults)

A seção defaults define tags que:
- sempre serão aplicadas
- não aceitam override
- prevalecem sobre qualquer valor informado externamente

Exemplo:

``` yaml
defaults:
  Owner: "data-platform"
  BusinessUnit: "ai"
```

Mesmo que um override tente alterar essas chaves, o valor do template será mantido.

---

### Tags dinâmicas (dynamic)

A seção dynamic define explicitamente quais tags podem variar.

``` yaml
dynamic:
  Environment: "{{ environment }}"
  ServiceType: "{{ service_type }}"
```

Somente essas chaves:
- podem ser sobrescritas via --overrides
- permitem variação por ambiente, serviço ou contexto
- mantêm a flexibilidade sem comprometer o padrão

---

Usando overrides com templates dinâmicos

Dado o template acima, é possível sobrescrever apenas campos definidos em dynamic:

``` bash
tago tag \
  --arn arn:aws:s3:::example-bucket \
  --template ./template.yaml \
  --overrides '{"environment":"prd","service_type":"api"}'
```

Resultado final aplicado:

``` yaml
{
  "Project": "vision-analytics",
  "Owner": "data-platform",
  "CostCenter": "CC-4022",
  "Department": "advanced-analytics",
  "BusinessUnit": "ai",
  "Usage": "machine-learning",
  "Environment": "prd",
  "ServiceType": "api"
}
```

---

## 📤 Formatos de saída

Por padrão, a saída é em **JSON**.  
Outros formatos disponíveis:

```bash
tago tag --arn ... --template ./template.yaml --output yaml
tago tag --arn ... --template ./template.yaml --output text
```

---

## 🧰 Comandos disponíveis

### `tag`

Aplica tags em recursos suportados com base em template e overrides.

```bash
tago tag \
  --arn arn:aws:s3:::my-bucket \
  --template ./template.yaml \
  --overrides '{"environment":"hml"}' \
  --dry-run
```

---

### `whoami`

Mostra o contexto de identidade AWS em uso:

```bash
tago whoami
```

---

### `adapters`

Lista todos os adapters disponíveis:

```bash
tago adapters
```

---

### `scan`

Varre recursos e compara contra um template:

```bash
tago scan s3 bucket --template ./template.yaml
```

> ⚠️ **Aviso importante**  
> scan é um comando altamente **experimental**, ele ainda não é confiável, deve sofrer mudanças consideráveis nos próximos ciclos de desenvolvimento e **não deve ser utilizado em ambientes produtivos**.  
---

## ⚙️ Configuração

O Tago usa a cadeia padrão de credenciais da AWS
(profiles, variáveis de ambiente, AWS SSO, etc).

Quando necessário, é possível especificar:

```bash
--profile <profile>
--region <region>
```

---

## 🛣️ Roadmap

- [x] Suporte a tagging via adapters para múltiplos serviços AWS
- [x] Dry-run para preview seguro
- [ ] Comando `scan`

---

## 🤖 Uso de IA no desenvolvimento

Este projeto utilizou ferramentas de **Inteligência Artificial** como apoio ao desenvolvimento,
sempre que apropriado, principalmente para:
- revisão de código
- refatoração
- escrita de testes
- documentação

Todas as decisões finais de arquitetura, lógica e implementação
foram revisadas e validadas manualmente.

---

## 🤝 Contribuição

Contribuições são bem-vindas.
Abra uma issue ou PR com contexto claro, motivação e exemplos quando possível.

---

## 📄 Licença

Veja o arquivo [`LICENSE`](LICENSE).
