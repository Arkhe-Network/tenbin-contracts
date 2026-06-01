// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";
import "../src/ZkCBDC.sol";

contract ZkCBDCTest is Test {
    ZkCBDC public cbdc;

    address centralBank = address(this);
    address alice = address(0x1);
    address bob = address(0x2);
    address eve = address(0x3);

    bytes32 dummyCommitment = keccak256("dummy");

    function setUp() public {
        cbdc = new ZkCBDC(1000000000);
    }

    function testCreateAccount() public {
        cbdc.createAccount(alice, dummyCommitment);
        (bytes32 commitment, , bool isFrozen, uint8 kycLevel, ) = cbdc.accounts(alice);
        assertEq(commitment, dummyCommitment);
        assertFalse(isFrozen);
        assertEq(kycLevel, 1);
    }

    function testSubmitTransaction() public {
        cbdc.createAccount(alice, dummyCommitment);
        cbdc.createAccount(bob, dummyCommitment);

        bytes32 txId = keccak256("tx1");
        bytes32 nullifier = keccak256("nullifier1");

        cbdc.submitTransaction(
            alice,
            bob,
            txId,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            nullifier,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            1000
        );

        (,,,,,,,, , ZkCBDC.TransactionStatus status,,) = cbdc.transactions(txId);

        assertTrue(uint(status) == uint(ZkCBDC.TransactionStatus.PROVEN));
        assertEq(cbdc.totalTransactions(), 1);
        assertEq(cbdc.totalVolume(), 1000);
        assertTrue(cbdc.nullifiers(nullifier));
    }

    function testDoubleSpendDetection() public {
        cbdc.createAccount(alice, dummyCommitment);
        cbdc.createAccount(bob, dummyCommitment);

        bytes32 txId1 = keccak256("tx1");
        bytes32 nullifier = keccak256("nullifier1");

        cbdc.submitTransaction(
            alice,
            bob,
            txId1,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            nullifier,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            1000
        );

        bytes32 txId2 = keccak256("tx2");

        vm.expectRevert("DOUBLE SPEND DETECTED");
        cbdc.submitTransaction(
            alice,
            bob,
            txId2,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            nullifier, // reuse nullifier
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            500
        );
    }

    function testSanctionsRejection() public {
        cbdc.createAccount(eve, dummyCommitment);
        cbdc.createAccount(bob, dummyCommitment);

        cbdc.addToSanctionsList(eve);

        bytes32 txId = keccak256("tx1");
        bytes32 nullifier = keccak256("nullifier1");

        cbdc.submitTransaction(
            eve,
            bob,
            txId,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            nullifier,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            1000
        );

        (,,,,,,,, , ZkCBDC.TransactionStatus status,,) = cbdc.transactions(txId);
        assertTrue(uint(status) == uint(ZkCBDC.TransactionStatus.REJECTED));
    }

    function testFrozenAccount() public {
        cbdc.createAccount(alice, dummyCommitment);
        cbdc.createAccount(bob, dummyCommitment);

        cbdc.freezeAccount(alice);

        bytes32 txId = keccak256("tx1");
        bytes32 nullifier = keccak256("nullifier1");

        cbdc.submitTransaction(
            alice,
            bob,
            txId,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            nullifier,
            dummyCommitment,
            dummyCommitment,
            dummyCommitment,
            1000
        );

        (,,,,,,,, , ZkCBDC.TransactionStatus status,,) = cbdc.transactions(txId);
        assertTrue(uint(status) == uint(ZkCBDC.TransactionStatus.REJECTED));
    }
}
