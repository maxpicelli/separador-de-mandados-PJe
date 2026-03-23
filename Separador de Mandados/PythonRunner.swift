import Foundation
import AppKit
import UniformTypeIdentifiers

enum PythonRunnerError: Error, LocalizedError {
    case scriptNotFound
    case pythonNotFound
    case userCanceled
    case depsInstallFailed(details: String)
    case runtimeNotReady(details: String)
    case nonZeroExit(status: Int32, stderr: String)

    var errorDescription: String? {
        switch self {
        case .scriptNotFound:
            return "Script embutido não encontrado no app."
        case .pythonNotFound:
            return "Python não encontrado (venv/Sistema)."
        case .userCanceled:
            return "Operação cancelada pelo usuário."
        case .depsInstallFailed(let d):
            return "Dependências do Python não disponíveis. \(d)"
        case .runtimeNotReady(let d):
            return "Ambiente Python não ficou pronto. \(d)"
        case .nonZeroExit(let s, let e):
            return "Python terminou com status \(s). \(e)"
        }
    }
}

struct PythonRunner {
    static func bundledScriptURL() -> URL? {
        Bundle.main.url(forResource: "separador_mandados", withExtension: "py")
    }

    // Ordem: venv do app (se existir) -> /usr/bin/python3 -> (opcional) Homebrew
    private static func candidatePythons() -> [URL] {
        var c: [URL] = []
        if let res = Bundle.main.resourceURL {
            c.append(res.appendingPathComponent("venv/bin/python3"))
        }
        c.append(URL(fileURLWithPath: "/usr/bin/python3"))
        // Se quiser considerar Homebrew, deixe esta linha. Caso não, remova.
        c.append(URL(fileURLWithPath: "/opt/homebrew/bin/python3"))
        return c
    }

    private static func pickPython(promptIfMissing: Bool = true) throws -> URL {
        for u in candidatePythons() where FileManager.default.isExecutableFile(atPath: u.path) {
            return u
        }
        guard promptIfMissing, let custom = promptChoosePython() else {
            throw PythonRunnerError.pythonNotFound
        }
        return custom
    }

    private static func promptChoosePython() -> URL? {
        var chosen: URL?
        runOnMainSync {
            let p = NSOpenPanel()
            p.title = "Escolha o binário do Python (python3)"
            p.allowsMultipleSelection = false
            p.canChooseFiles = true
            p.canChooseDirectories = false
            if #available(macOS 12.0, *) {
                p.allowedContentTypes = [.unixExecutable]
            } else {
                p.allowedFileTypes = ["public.unix-executable"]
            }
            p.allowsOtherFileTypes = true
            p.directoryURL = URL(fileURLWithPath: "/usr/bin")
            if p.runModal() == .OK, let url = p.url,
               FileManager.default.isExecutableFile(atPath: url.path) {
                chosen = url
            }
        }
        return chosen
    }

    private static func isBundledVenv(_ python: URL) -> Bool {
        python.standardizedFileURL.path.contains("/Contents/Resources/venv/")
    }

    private static func makeEnvironment(for python: URL) -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env["PIP_NO_CACHE_DIR"] = "1"
        env["LC_ALL"] = "en_US.UTF-8"
        env["LANG"] = "en_US.UTF-8"

        if isBundledVenv(python) {
            env["PYTHONNOUSERSITE"] = "1"
            env["PYTHONPATH"] = ""
        } else {
            env.removeValue(forKey: "PYTHONNOUSERSITE")
            env.removeValue(forKey: "PYTHONPATH")
        }

        return env
    }

    private static func execute(
        executableURL: URL,
        arguments: [String],
        currentDirectoryURL: URL? = nil,
        environment: [String: String]? = nil
    ) throws -> (status: Int32, stdout: String, stderr: String) {
        let task = Process()
        task.executableURL = executableURL
        task.arguments = arguments
        task.currentDirectoryURL = currentDirectoryURL
        task.environment = environment

        let outPipe = Pipe()
        let errPipe = Pipe()
        task.standardOutput = outPipe
        task.standardError = errPipe

        try task.run()
        task.waitUntilExit()

        let stdout = String(data: outPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let stderr = String(data: errPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""

        return (task.terminationStatus, stdout, stderr)
    }

    @discardableResult
    static func prepareRuntime() throws -> String {
        let python = try pickPython()
        let env = makeEnvironment(for: python)
        let readinessCheck = "import PyPDF2, pdfplumber; print('PYTHON_RUNTIME_READY')"

        let initial = try execute(
            executableURL: python,
            arguments: ["-c", readinessCheck],
            environment: env
        )

        if initial.status == 0 {
            return "Runtime Python pronto: \(python.path)"
        }

        let installArgs: [String]
        if isBundledVenv(python) {
            installArgs = ["-m", "pip", "install", "PyPDF2", "pdfplumber"]
        } else {
            installArgs = ["-m", "pip", "install", "--user", "PyPDF2", "pdfplumber"]
        }

        let install = try execute(
            executableURL: python,
            arguments: installArgs,
            environment: env
        )

        if install.status != 0 {
            let details = install.stderr.isEmpty ? install.stdout : install.stderr
            throw PythonRunnerError.depsInstallFailed(details: details.trimmingCharacters(in: .whitespacesAndNewlines))
        }

        let retry = try execute(
            executableURL: python,
            arguments: ["-c", readinessCheck],
            environment: env
        )

        if retry.status != 0 {
            let details = retry.stderr.isEmpty ? retry.stdout : retry.stderr
            throw PythonRunnerError.runtimeNotReady(details: details.trimmingCharacters(in: .whitespacesAndNewlines))
        }

        let installSummary = install.stdout.isEmpty ? install.stderr : install.stdout
        let summary = installSummary.trimmingCharacters(in: .whitespacesAndNewlines)
        return summary.isEmpty ? "Dependências instaladas e runtime pronto: \(python.path)" : summary
    }

    @discardableResult
    static func run(script: URL, withTarget target: URL, outputDir: URL) throws -> String {
        let python = try pickPython()
        let result = try execute(
            executableURL: python,
            arguments: [script.path, target.path, outputDir.path],
            currentDirectoryURL: script.deletingLastPathComponent(),
            environment: makeEnvironment(for: python)
        )

        if result.status != 0 {
            throw PythonRunnerError.nonZeroExit(status: result.status, stderr: result.stderr.isEmpty ? result.stdout : result.stderr)
        }
        return result.stdout.isEmpty ? (result.stderr.isEmpty ? "OK" : result.stderr) : result.stdout
    }

    @discardableResult
    private static func runOnMainSync<T>(_ block: () -> T) -> T {
        if Thread.isMainThread { return block() }
        var result: T!
        DispatchQueue.main.sync { result = block() }
        return result
    }
}
