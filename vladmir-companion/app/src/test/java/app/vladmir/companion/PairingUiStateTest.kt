package app.vladmir.companion

import org.junit.Assert.*
import org.junit.Test

class PairingUiStateTest {
    @Test fun unsolicitedPermissionResultDoesNotNavigate() {
        val state=PairingUiState()
        assertFalse(state.permissionResult(true,true));assertFalse(state.consumeResumeChoice())
    }
    @Test fun foregroundGrantContinuesTheExplicitRequest() {
        val state=PairingUiState();state.requestPermission()
        assertTrue(state.permissionResult(true,true));assertFalse(state.consumeResumeChoice())
        assertFalse(state.permissionResult(true,true))
    }
    @Test fun backgroundGrantDefersExactlyOnceUntilResume() {
        val state=PairingUiState();state.requestPermission()
        assertFalse(state.permissionResult(true,false));assertTrue(state.consumeResumeChoice());assertFalse(state.consumeResumeChoice())
    }
    @Test fun refusalNeverContinues() {
        val state=PairingUiState();state.requestPermission()
        assertFalse(state.permissionResult(false,true));assertFalse(state.consumeResumeChoice())
    }
    @Test fun pendingCancellationIsExplainedOnce() {
        val state=PairingUiState();state.pendingCancelled(true)
        assertTrue(state.consumeCancellation());assertFalse(state.consumeCancellation())
    }
    @Test fun existingAuthorizedServiceDoesNotCreatePendingCancellationNotice() {
        val state=PairingUiState();state.pendingCancelled(false)
        assertFalse(state.consumeCancellation())
    }
    @Test fun newPermissionRequestClearsAnOldDeferredContinuation() {
        val state=PairingUiState();state.requestPermission();state.permissionResult(true,false);state.requestPermission()
        assertFalse(state.consumeResumeChoice());assertFalse(state.permissionResult(false,true))
    }
    @Test fun knownWearDeviceAppearsBeforeBluetoothAudioAccessories() {
        assertEquals(listOf("Generic Wear Watch","Bluetooth Audio A","Bluetooth Audio B"),
            WearPeerOrder.prioritizeWearDevice(listOf("Bluetooth Audio B","Generic Wear Watch","Bluetooth Audio A")){it})
    }
}
