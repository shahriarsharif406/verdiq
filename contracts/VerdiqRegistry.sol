// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title VerdiqRegistry - on-chain double-counting firewall for carbon credits
/// @notice Serial ranges are intervals [start, end] (inclusive). The registry keeps a sorted, non-overlapping list of
///         segments covering everything ever issued. A range can only be transferred or retired by its current owner,
///         only once, and never while a host country counts the same tonnes without a corresponding adjustment.
/// @dev    SYNTHETIC / DEMO CODE. Storage uses a sorted array with O(n) splits - fine for a demo ledger, not production scale.
///         Revert reasons are short machine codes that the off-chain engine maps to its rule ids:
///         OVERLAP_ISSUANCE, NOT_ISSUED, NOT_OWNER, RETIRED, ALREADY_RETIRED, DOUBLE_CLAIM, HOST_DOUBLE_CLAIM, ...
contract VerdiqRegistry {
    enum State { ACTIVE, RETIRED }

    struct Segment {
        uint64 start;
        uint64 end;
        State state;
        address owner;
        bytes32 claimedFor; // set when retired
    }

    struct HostClaim {
        bytes2 country;
        uint64 start;
        uint64 end;
        bool correspondingAdjustment;
    }

    address public immutable authority;
    Segment[] private segs;
    HostClaim[] private hostClaims;
    mapping(uint32 => bytes32) public closeRoot; // yyyymmdd => Merkle root of that day's reconciliation snapshot

    event Issued(bytes32 indexed projectId, address indexed developer, uint64 start, uint64 end, uint16 vintage);
    event Transferred(address indexed from, address indexed to, uint64 start, uint64 end);
    event Retired(address indexed owner, uint64 start, uint64 end, bytes32 claimedFor);
    event HostClaimRegistered(bytes2 indexed country, uint64 start, uint64 end, bool correspondingAdjustment);
    event CloseAnchored(uint32 indexed date, bytes32 root);

    modifier onlyAuthority() {
        require(msg.sender == authority, "NOT_AUTHORITY");
        _;
    }

    constructor() {
        authority = msg.sender;
    }

    // ------------------------------------------------------------------ issuance
    function issue(address developer, bytes32 projectId, uint64 start, uint64 end, uint16 vintage) external onlyAuthority {
        require(start <= end, "BAD_RANGE");
        uint256 i = _firstIndexEndingAtOrAfter(start);
        require(i == segs.length || segs[i].start > end, "OVERLAP_ISSUANCE");
        _insertAt(i, Segment(start, end, State.ACTIVE, developer, bytes32(0)));
        emit Issued(projectId, developer, start, end, vintage);
    }

    // ------------------------------------------------------------------ transfer
    function transfer(uint64 start, uint64 end, address to) external {
        require(start <= end, "BAD_RANGE");
        require(to != address(0), "BAD_RECIPIENT");
        (uint256 lo, uint256 hi) = _isolate(start, end, msg.sender, false, bytes32(0));
        for (uint256 i = lo; i <= hi; i++) segs[i].owner = to;
        emit Transferred(msg.sender, to, start, end);
    }

    // ------------------------------------------------------------------ retirement
    function retire(uint64 start, uint64 end, bytes32 claimedFor) external {
        require(start <= end, "BAD_RANGE");
        require(!_hostConflict(start, end), "HOST_DOUBLE_CLAIM");
        (uint256 lo, uint256 hi) = _isolate(start, end, msg.sender, true, claimedFor);
        for (uint256 i = lo; i <= hi; i++) {
            segs[i].state = State.RETIRED;
            segs[i].claimedFor = claimedFor;
        }
        emit Retired(msg.sender, start, end, claimedFor);
    }

    // ------------------------------------------------------------------ Article 6 host-country claims
    /// @notice A host country records that it counts these tonnes toward its NDC. Without a corresponding adjustment this
    ///         is only allowed if no company has retired the same tonnes (and blocks later retirement of them).
    function registerHostClaim(bytes2 country, uint64 start, uint64 end, bool correspondingAdjustment) external onlyAuthority {
        require(start <= end, "BAD_RANGE");
        if (!correspondingAdjustment) {
            uint256 i = _firstIndexEndingAtOrAfter(start);
            while (i < segs.length && segs[i].start <= end) {
                require(segs[i].state != State.RETIRED, "HOST_DOUBLE_CLAIM");
                i++;
            }
        }
        hostClaims.push(HostClaim(country, start, end, correspondingAdjustment));
        emit HostClaimRegistered(country, start, end, correspondingAdjustment);
    }

    // ------------------------------------------------------------------ Day-End Close
    function anchorClose(uint32 date, bytes32 root) external onlyAuthority {
        require(closeRoot[date] == bytes32(0), "ALREADY_ANCHORED");
        require(root != bytes32(0), "EMPTY_ROOT");
        closeRoot[date] = root;
        emit CloseAnchored(date, root);
    }

    /// @notice Verify that `record` (canonical JSON bytes) was part of the snapshot anchored on `date`.
    ///         leaf = sha256(0x00 || record); parent = sha256(0x01 || min(a,b) || max(a,b)). Matches engine/merkle.py.
    function verifyRecord(uint32 date, bytes calldata record, bytes32[] calldata proof) external view returns (bool) {
        bytes32 root = closeRoot[date];
        if (root == bytes32(0)) return false;
        bytes32 h = sha256(abi.encodePacked(bytes1(0x00), record));
        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 p = proof[i];
            h = h <= p ? sha256(abi.encodePacked(bytes1(0x01), h, p)) : sha256(abi.encodePacked(bytes1(0x01), p, h));
        }
        return h == root;
    }

    // ------------------------------------------------------------------ views
    function segmentCount() external view returns (uint256) {
        return segs.length;
    }

    function segmentAt(uint256 i) external view returns (Segment memory) {
        return segs[i];
    }

    function ownerOf(uint64 serial) external view returns (bool issued, address owner, State state) {
        uint256 i = _firstIndexEndingAtOrAfter(serial);
        if (i == segs.length || segs[i].start > serial) return (false, address(0), State.ACTIVE);
        return (true, segs[i].owner, segs[i].state);
    }

    /// @notice Dry-run helper: returns "" if the sender could retire/transfer the range, else the revert code.
    function dryRun(bool isRetire, address actor, uint64 start, uint64 end, bytes32 claimedFor) external view returns (string memory) {
        if (start > end) return "BAD_RANGE";
        if (isRetire && _hostConflict(start, end)) return "HOST_DOUBLE_CLAIM";
        return _validate(start, end, actor, isRetire, claimedFor);
    }

    // ------------------------------------------------------------------ internals
    function _hostConflict(uint64 start, uint64 end) internal view returns (bool) {
        for (uint256 i = 0; i < hostClaims.length; i++) {
            HostClaim storage h = hostClaims[i];
            if (!h.correspondingAdjustment && h.start <= end && h.end >= start) return true;
        }
        return false;
    }

    /// @dev index of the first segment whose end >= x (segments are sorted and disjoint), or segs.length.
    function _firstIndexEndingAtOrAfter(uint64 x) internal view returns (uint256) {
        uint256 lo = 0;
        uint256 hi = segs.length;
        while (lo < hi) {
            uint256 mid = (lo + hi) / 2;
            if (segs[mid].end < x) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }

    function _validate(uint64 start, uint64 end, address actor, bool isRetire, bytes32 claimedFor)
        internal view returns (string memory)
    {
        uint256 i = _firstIndexEndingAtOrAfter(start);
        if (i == segs.length || segs[i].start > start) return "NOT_ISSUED";
        uint64 cur = start;
        while (cur <= end) {
            if (i >= segs.length || segs[i].start > cur) return "NOT_ISSUED";
            Segment storage s = segs[i];
            if (s.state == State.RETIRED) {
                if (!isRetire) return "RETIRED";
                return s.claimedFor == claimedFor ? "ALREADY_RETIRED" : "DOUBLE_CLAIM";
            }
            if (s.owner != actor) return "NOT_OWNER";
            if (s.end == type(uint64).max) break;
            cur = s.end + 1;
            i++;
        }
        return "";
    }

    /// @dev validates, splits at the boundaries, returns the inclusive index span of the segments covering [start, end].
    function _isolate(uint64 start, uint64 end, address actor, bool isRetire, bytes32 claimedFor)
        internal returns (uint256 lo, uint256 hi)
    {
        string memory why = _validate(start, end, actor, isRetire, claimedFor);
        require(bytes(why).length == 0, why);
        _splitBefore(start);
        if (end != type(uint64).max) _splitBefore(end + 1);
        lo = _firstIndexEndingAtOrAfter(start);
        hi = lo;
        while (hi + 1 < segs.length && segs[hi].end < end) hi++;
    }

    function _splitBefore(uint64 at) internal {
        uint256 i = _firstIndexEndingAtOrAfter(at);
        if (i == segs.length) return;
        Segment memory s = segs[i];
        if (s.start < at && at <= s.end) {
            segs[i].end = at - 1;
            _insertAt(i + 1, Segment(at, s.end, s.state, s.owner, s.claimedFor));
        }
    }

    function _insertAt(uint256 i, Segment memory s) internal {
        uint256 n = segs.length;
        if (i == n) {
            segs.push(s);
            return;
        }
        segs.push(segs[n - 1]);
        for (uint256 j = n - 1; j > i; j--) segs[j] = segs[j - 1];
        segs[i] = s;
    }
}
