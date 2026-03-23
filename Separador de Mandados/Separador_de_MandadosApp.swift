import SwiftUI

@main
struct Separador_de_MandadosApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 1110, idealWidth: 1110, minHeight: 840, idealHeight: 840)
        }
        .windowResizability(.contentSize)  // Respeita o tamanho do conteúdo
        .commands {
            // Remove o menu "New" se não for necessário
            CommandGroup(replacing: .newItem) { }
        }
    }
}
